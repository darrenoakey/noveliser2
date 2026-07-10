"""Embedding-based retrieval memory for story continuity.

Replaces the old per-section LLM fact-extraction + contradiction-regeneration
loop with a lightweight vector memory:

  * Every sentence of written prose is embedded (remotely, on the spark GPU box
    via the SDK's arbiter embeddings — so this process holds NO model in memory)
    and stored.
  * Before writing the next section we retrieve the most relevant prior
    sentences and feed them back into the prompt as "established details".

So "facts" are identified (every sentence) and stored (the vector index), and
made accessible to the writer through similarity retrieval — no big-model call
per section, no regeneration. Cosine search is pure Python (a few thousand
768-dim vectors at most), so nothing heavy runs locally.
"""

from __future__ import annotations

import asyncio
import json
import math
import re
import time
from pathlib import Path

from daz_agent_sdk import AgentError, agent

# a remote arbiter embedding job occasionally dies transiently (subprocess
# crash on the GPU box) — bounded retry with backoff so one flaky job doesn't
# abort an entire multi-hour novel generation run.
_EMBED_MAX_ATTEMPTS = 3
_EMBED_RETRY_DELAY_SECONDS = 5.0

# nomic-style task prefixes: documents and queries are embedded differently.
_DOC_TASK = "search_document"
_QUERY_TASK = "search_query"

# sentences shorter than this carry no retrievable signal (e.g. "He nodded.").
_MIN_SENTENCE_CHARS = 25
# but a SHORT sentence that names a proper-noun entity is usually a hard fact
# ("Rex was a beagle." — 18 chars) and must survive; keep those down to this floor.
_MIN_ENTITY_SENTENCE_CHARS = 8
# cap stored sentence length so one runaway sentence can't dominate a prompt.
_MAX_SENTENCE_CHARS = 400

# common sentence-initial words that are capitalized but are NOT proper nouns —
# used to tell "Rex ..." (keep) from "He ..." / "The ..." (drop) in short sentences.
_NON_ENTITY_CAPS = {
    "he", "she", "it", "they", "we", "you", "i", "the", "a", "an", "but", "and",
    "or", "so", "then", "there", "this", "that", "these", "those", "his", "her",
    "its", "their", "our", "your", "my", "when", "while", "as", "after", "before",
    "if", "no", "yes", "why", "how", "what", "who", "still", "now", "here", "for",
    "with", "at", "on", "in", "of", "to",
}


# ##################################################################
# proper-noun detection
# true if the sentence contains a capitalized token that looks like a name/place
# rather than a mere sentence-initial pronoun/article. Cheap heuristic, no NLP.
def _has_proper_noun(sentence: str) -> bool:
    for token in re.findall(r"[A-Z][a-zA-Z'’-]+", sentence):
        if token.lower() not in _NON_ENTITY_CAPS:
            return True
    return False


# ##################################################################
# split into sentences
# cheap, dependency-free sentence splitter. fiction has dialogue and varied
# punctuation, so this is approximate — that is fine, retrieval is robust to
# imperfect boundaries.
def split_sentences(text: str) -> list[str]:
    collapsed = re.sub(r"\s+", " ", text.strip())
    if not collapsed:
        return []
    raw = re.split(r"(?<=[.!?])\s+(?=[\"'“‘A-Z0-9])", collapsed)
    out: list[str] = []
    for s in raw:
        s = s.strip()
        if len(s) < _MIN_SENTENCE_CHARS:
            # rescue short declarative facts that name a proper-noun entity
            # (e.g. "Rex was a beagle.") — these are exactly the continuity
            # anchors we must not drop. Pure pronoun/article shorts still go.
            if len(s) < _MIN_ENTITY_SENTENCE_CHARS or not _has_proper_noun(s):
                continue
        out.append(s[:_MAX_SENTENCE_CHARS])
    return out


# ##################################################################
# embed texts
# batch-embed a list of strings via the remote arbiter embeddings endpoint.
# returns one vector per input. runs no model in this process.
def _embed(texts: list[str], task: str) -> list[list[float]]:
    if not texts:
        return []

    async def _run() -> list[list[float]]:
        result = await agent.embed(texts, task=task)
        return list(result.embeddings)

    last_error: AgentError | None = None
    for attempt in range(1, _EMBED_MAX_ATTEMPTS + 1):
        try:
            return asyncio.run(_run())
        except AgentError as e:
            last_error = e
            if attempt < _EMBED_MAX_ATTEMPTS:
                time.sleep(_EMBED_RETRY_DELAY_SECONDS * attempt)
    assert last_error is not None
    raise last_error


# ##################################################################
# cosine similarity
# both vectors are raw; norms are computed on the fly. pure python is plenty
# fast for the few-thousand-vector indexes a single novel produces.
def _cosine(a: list[float], b: list[float]) -> float:
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


# ##################################################################
# memory entry
# a single stored sentence and its embedding, tagged with its section.
class _Entry:
    __slots__ = ("section_id", "sentence", "embedding")

    def __init__(self, section_id: str, sentence: str, embedding: list[float]) -> None:
        self.section_id = section_id
        self.sentence = sentence
        self.embedding = embedding


# ##################################################################
# retrieval memory
# persistent per-novel sentence/embedding store with similarity retrieval.
class RetrievalMemory:
    def __init__(self) -> None:
        self._entries: list[_Entry] = []
        self._sections: set[str] = set()
        # sections in first-seen (write) order, so recency can be scored as a
        # section's position in the novel without parsing "chN.sM" strings.
        self._section_order: list[str] = []

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, section_id: str) -> bool:
        return section_id in self._sections

    def sections(self) -> set[str]:
        return set(self._sections)

    # ##################################################################
    # ensure section
    # idempotently embed and store a section's sentences. safe to call again
    # on resume — a section already present is skipped, so no re-embedding.
    def ensure_section(self, section_id: str, text: str) -> int:
        if section_id in self._sections:
            return 0
        sentences = split_sentences(text)
        embeddings = _embed(sentences, _DOC_TASK)
        for sentence, embedding in zip(sentences, embeddings):
            self._entries.append(_Entry(section_id, sentence, embedding))
        self._sections.add(section_id)
        if section_id not in self._section_order:
            self._section_order.append(section_id)
        return len(sentences)

    # ##################################################################
    # recency boost
    # normalized [0, 1] position of a section in write order (1.0 = newest). Used
    # to gently favour more recent sections so a corrected fact stored later can
    # surface over a stale but more similar-sounding original.
    def _recency_boost(self, section_id: str) -> float:
        n = len(self._section_order)
        if n <= 1:
            return 1.0
        try:
            idx = self._section_order.index(section_id)
        except ValueError:
            return 0.0
        return idx / (n - 1)

    # ##################################################################
    # retrieve
    # return up to k stored sentences most relevant to the query, optionally
    # excluding a section (e.g. the one currently being written). results are
    # ordered most-relevant first.
    def retrieve(self, query: str, k: int = 12, exclude_section: str | None = None,
                 recency_weight: float = 0.15) -> list[str]:
        if not self._entries or not query.strip():
            return []
        q = _embed([query], _QUERY_TASK)[0]
        scored: list[tuple[float, str]] = []
        for entry in self._entries:
            if exclude_section is not None and entry.section_id == exclude_section:
                continue
            # blend cosine similarity with a small recency bonus. The bonus is
            # dominated by real similarity, but it breaks near-ties in favour of
            # newer sections so a later correction can outrank a stale original
            # that happens to phrase itself more like the query.
            score = _cosine(q, entry.embedding)
            if recency_weight:
                score += recency_weight * self._recency_boost(entry.section_id)
            scored.append((score, entry.sentence))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [sentence for _, sentence in scored[:k]]

    # ##################################################################
    # persistence
    def to_json(self) -> list[dict]:
        return [
            {"section_id": e.section_id, "sentence": e.sentence, "embedding": e.embedding}
            for e in self._entries
        ]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_json(), fh, ensure_ascii=False)

    @classmethod
    def load(cls, path: Path) -> "RetrievalMemory":
        memory = cls()
        if not path.exists():
            return memory
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for entry in data:
            sid = entry["section_id"]
            memory._entries.append(_Entry(sid, entry["sentence"], entry["embedding"]))
            memory._sections.add(sid)
            if sid not in memory._section_order:
                memory._section_order.append(sid)
        return memory
