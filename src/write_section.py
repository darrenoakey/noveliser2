"""Prose generation for a single section — the integration layer.

This module wires together the craft helpers (canon facts, name roster, voice,
adaptive word targets), the retrieval memory, the (optional) fact ledger, and a
set of small, non-blocking quality guards:

* CANON FACTS block from the fact ledger, authoritative and separate from the
  soft "ESTABLISHED DETAILS" retrieval list (#2, #27).
* Broadened retrieval query that also pulls named entities out of the character
  sheets, not just character names (#11).
* Compact prior-chapter summaries as long-term memory, distinct from the raw
  text window and the retrieval pool (#14).
* Near-duplicate section guard bounded to exactly one retry (#16, #85).
* Verbatim name-spelling roster in every prompt (#28).
* Non-blocking plan-vs-prose drift log (#30).
* One optional, feature-flagged revision pass (#36, #85).
* Repetition guard against the manuscript-so-far (#38).
* Adaptive per-scene word target (#41) and structured POV/tense (#42).
* The escalated PROSE_TIER on the prose call only (#46).
* Prior-section-ending recap for smooth transitions (#65).
* A real `SectionResult.new_facts`, populated from the ledger (#76).

Nothing here regenerates a whole section on a consistency failure — every guard
either logs, annotates, or (for the bounded dedup case) retries at most once.
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from daz_agent_sdk import Tier

from models import (
    Chapter,
    ChapterPlan,
    Character,
    Fact,
    Section,
    SectionResult,
    WritingStyle,
)
from retrieval_memory import RetrievalMemory

from pydantic import BaseModel, Field

from brain import PROSE_TIER, TIER, chat, chat_structured
from craft import (
    PROSE_CRAFT,
    render_canon_facts,
    render_character_arcs,
    render_character_engine,
    render_character_voice,
    render_name_roster,
    render_plot_threads,
    word_target_for_scene,
)

# how many prior sentences to retrieve as "established details" for a section
RETRIEVAL_K = 12

# ##################################################################
# feature flags (#85)
# ENABLE_REVISION_PASS defaults ON: a real end-to-end test novel showed the
# exact defects this pass targets — overused setting phrases repeated across
# multiple sections ("edge of the marsh") and planned climactic beats silently
# dropped from the prose (a bribery attempt, a viral social-media turn) — were
# being logged by ENABLE_DRIFT_LOG but never corrected, because the pass that
# consumes those signals was gated off. The extra critique-and-line-edit call
# doubles per-section prose cost, but leaving proven, planned drama out of a
# generated novel is a worse defect than the added latency. The near-dup retry
# and drift/repetition logging are cheap regardless, so they stay ON too.
ENABLE_REVISION_PASS = True
ENABLE_DEDUP_RETRY = True
ENABLE_DRIFT_LOG = True

# a generated section is treated as a near-duplicate of the one before it when
# their word-level SequenceMatcher ratio meets this (matches analyze_novel.py).
DEDUP_THRESHOLD = 0.6
# a distinctive 3+word phrase repeated at least this many times across the
# manuscript so far is flagged as over-used (#38).
NGRAM_REPEAT_THRESHOLD = 5

CONTINUITY_WARNINGS_FILE = "continuity_warnings.json"

# minimal closed-class stop set for the drift/entity heuristics (kept local so
# this module stays decoupled from analyze_novel's private internals).
_STOPWORDS = frozenset(
    "the a an and or but of to in on at for with from by as is was were be been "
    "being it its he she they them his her their you your i we our that this these "
    "those had has have do did not no so if then than there here into out over "
    "up down off about after before while when where who whom which what how".split()
)
_WORD_RE = re.compile(r"[A-Za-z'’]+")
_PROPER_RE = re.compile(r"\b([A-Z][a-zA-Z’'\-]{2,})\b")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[\"'“‘A-Z0-9])")
_THINK_RE = re.compile(r"<\s*(think|thinking|reasoning)\s*>.*?<\s*/\s*\1\s*>", re.IGNORECASE | re.DOTALL)
_NUMBERED_BOLD_HEADER_RE = re.compile(r"^\s*\d+\.\s*\*\*")
_META_MARKERS = (
    "analyze user input", "pov/tense:", "canon facts:", "canon/facts:",
    "dramatic shape:", "structure/goal:", "role/task:", "chapter/section:",
)

_DEDUP_RETRY_INSTRUCTION = (
    "\n\nIMPORTANT: Do NOT repeat or lightly reword the previous scene. The draft that "
    "would naturally follow here is too similar to the section just written. Write a "
    "GENUINELY NEW scene that advances the story — different setting, action, and beats — "
    "while staying consistent with the established facts."
)

# #91/#93 — a reasoning-tier model occasionally produces invalid prose: either
# its own planning notes (a numbered, markdown-bold-headed breakdown of
# POV/style/canon facts/etc.) with no <think> wrapper for _strip_think to
# catch, or a response that stops mid-sentence far short of the target length
# (the "thinking" budget crowds out the visible answer). Both are bounded to
# exactly one same-tier retry, then one fallback-tier retry on the reliable
# non-reasoning TIER; if that also fails, raise rather than silently saving
# broken text as the novel's prose.
_INVALID_PROSE_RETRY_INSTRUCTION = (
    "\n\nCRITICAL: Your previous response was invalid — either your own "
    "planning/analysis notes (headers, numbered lists, labels like 'POV/Tense:' or "
    "'Canon Facts:') instead of a story, or it stopped abruptly mid-sentence far "
    "short of the target length. Do not repeat that mistake. Output ONLY complete, "
    "flowing narrative prose at the requested length — no headers, no bullet "
    "points, no bold labels, no restating these instructions, and finish every "
    "sentence and the scene itself before stopping."
)


# ##################################################################
# write section
# generate the prose for one section, applying all integration-layer guards.
# ledger is duck-typed (the fact_ledger.FactLedger, or None when unavailable);
# prior_summaries is the compact long-term chapter memory; prev_section_text is
# the immediately preceding section's prose (for the dedup guard + recap).
def write_section(chapter: Chapter, section: Section, previous_text: str,
                  memory: RetrievalMemory, characters: list[Character],
                  writing_style: WritingStyle, chapter_plan: ChapterPlan,
                  is_final_section: bool, ledger=None, prior_summaries: str = "",
                  prev_section_text: str = "", novel_dir: Path | None = None,
                  plots=None, arcs=None,
                  enable_revision_pass: bool = ENABLE_REVISION_PASS) -> SectionResult:
    is_first = chapter.number == 1 and section.number == 1
    section_id = f"ch{chapter.number}.s{section.number}"

    all_chapters_summary = "\n".join([
        f"Chapter {c.number}: {c.title} - {c.chapter_goal} (ends: {c.closing_situation})"
        for c in chapter_plan.chapters
    ])

    position_note = "Begin the story." if is_first else "Continue the narrative from where the previous text ended."
    if is_final_section:
        position_note += " This is the FINAL section. Bring the story to a satisfying conclusion."
    else:
        position_note += " Do NOT conclude or wrap up - there is more story to come after this section."

    previous_context = ""
    if previous_text:
        chars_to_include = min(len(previous_text), 8000)
        previous_context = f"\n\nTEXT SO FAR (last {chars_to_include} characters - continue from here):\n\n{previous_text[-chars_to_include:]}"

    # #65 — always carry the literal last few sentences of the previous section,
    # even when they fall outside the truncated raw-text window above.
    recap_block = ""
    recap = last_sentences(prev_section_text, 3)
    if recap and not is_first:
        recap_block = (
            "\n\nPREVIOUS SECTION ENDING (continue smoothly and immediately from this — "
            "do not restate it):\n" + recap + "\n"
        )

    # #14 — compact long-term chapter memory, distinct from the raw window and
    # the retrieval pool.
    summary_block = ""
    if prior_summaries.strip():
        summary_block = (
            "\n\nSTORY SO FAR (compact chapter summaries — long-term memory; keep continuity "
            "with these):\n" + prior_summaries.strip() + "\n"
        )

    character_names = [c.name for c in characters]
    scene_entities = extract_scene_entities(characters)

    # #2/#27/#28 — authoritative CANON FACTS block from the ledger (exact
    # spellings, breeds, physical traits) + a canonical name-spelling roster.
    canon_block = _render_canon_block(ledger, character_names, scene_entities)
    roster_block = render_name_roster(character_names + scene_entities)

    character_block = _render_characters(characters)
    engine_block = render_character_engine(characters)
    voice_block = _render_voices(characters)
    scene_directive = _render_scene_directive(section)

    # #11 — broadened retrieval query: goal + key events + character names AND
    # named entities/possessions drawn from the character sheets.
    query = build_retrieval_query(section, characters)
    established = memory.retrieve(query, k=RETRIEVAL_K, exclude_section=section_id)
    established_block = _render_established(established)

    lo, hi = word_target_for_scene(section)  # #41
    pov_tense = _render_pov_tense(writing_style)  # #42

    # compact plot-thread + trajectory blocks so the prose keeps every plot line
    # live and lands each character where their arc says (not the full stories).
    plot_block = render_plot_threads(plots)
    arc_block = render_character_arcs(arcs)

    prompt_ctx = _PromptContext(
        chapter=chapter, section=section, writing_style=writing_style,
        all_chapters_summary=all_chapters_summary, position_note=position_note,
        previous_context=previous_context, character_block=character_block,
        engine_block=engine_block, voice_block=voice_block,
        scene_directive=scene_directive, established_block=established_block,
        canon_block=canon_block, roster_block=roster_block,
        summary_block=summary_block, recap_block=recap_block,
        plot_block=plot_block, arc_block=arc_block,
        pov_tense=pov_tense, word_lo=lo, word_hi=hi,
    )

    # initial draft
    section_text = _postprocess(_generate_prose(prompt_ctx, ""))

    # #91/#93 — reasoning-tier model returned planning notes or a mid-sentence
    # truncation instead of a finished story. Bounded: one same-tier retry with
    # a reinforced instruction, then one fallback-tier retry on the reliable
    # non-reasoning TIER. If it's still invalid, raise — never save broken text
    # as the novel's text.
    defect = _invalid_prose_reason(section_text, lo)
    if defect:
        section_text = _postprocess(_generate_prose(prompt_ctx, _INVALID_PROSE_RETRY_INSTRUCTION))
        defect = _invalid_prose_reason(section_text, lo)
        if defect:
            section_text = _postprocess(
                _generate_prose(prompt_ctx, _INVALID_PROSE_RETRY_INSTRUCTION, tier=TIER)
            )
            defect = _invalid_prose_reason(section_text, lo)
            if defect:
                raise ValueError(
                    f"section {section_id}: {defect} after two retries "
                    "(including a non-reasoning-tier fallback)"
                )

    # #16 — near-duplicate guard, bounded to EXACTLY one retry.
    dedup_warning = None
    if ENABLE_DEDUP_RETRY and prev_section_text and is_near_duplicate(
        section_text, prev_section_text, DEDUP_THRESHOLD
    ):
        retry_text = _postprocess(_generate_prose(prompt_ctx, _DEDUP_RETRY_INSTRUCTION))
        still_dup = is_near_duplicate(retry_text, prev_section_text, DEDUP_THRESHOLD)
        section_text = retry_text
        if still_dup:
            dedup_warning = (
                f"section {section_id} still near-duplicate of the previous section after "
                f"one retry (ratio >= {DEDUP_THRESHOLD}); accepted anyway"
            )

    # #38 — repetition guard against the manuscript so far.
    overused = overused_ngrams(section_text, previous_text, NGRAM_REPEAT_THRESHOLD)
    # #30/#94 — plan-vs-prose drift: cheap keyword prefilter, then semantic
    # confirmation of the suspects so paraphrased beats don't get flagged.
    dropped_beats = confirm_dropped_beats(
        section_text, find_dropped_beats(section, section_text)
    )

    # #36 — one optional, gated revision pass; addresses over-used phrases and
    # dropped beats via targeted line edits, never a full regeneration.
    if enable_revision_pass:
        section_text = _postprocess(
            _revise_prose(section_text, overused, dropped_beats)
        )
        # recompute the log signals against the revised text
        overused = overused_ngrams(section_text, previous_text, NGRAM_REPEAT_THRESHOLD)
        dropped_beats = confirm_dropped_beats(
            section_text, find_dropped_beats(section, section_text)
        )

    if ENABLE_DRIFT_LOG:
        _log_continuity_warnings(
            novel_dir, section_id, dedup_warning, overused, dropped_beats
        )

    # #76 — populate new_facts for real from the ledger extraction.
    new_facts = _extract_facts(ledger, section_text, character_names + scene_entities, section_id)
    return SectionResult(text=section_text, new_facts=new_facts)


# ##################################################################
# prompt context
# groups every prompt fragment so the prose + revision calls share one shape.
class _PromptContext:
    __slots__ = (
        "chapter", "section", "writing_style", "all_chapters_summary",
        "position_note", "previous_context", "character_block", "engine_block",
        "voice_block", "scene_directive", "established_block", "canon_block",
        "roster_block", "summary_block", "recap_block", "plot_block",
        "arc_block", "pov_tense", "word_lo", "word_hi",
    )

    def __init__(self, **kw) -> None:
        for k, v in kw.items():
            setattr(self, k, v)


# ##################################################################
# build retrieval query (#11)
# broaden the retrieval query beyond goal + key_events + character names to also
# include named entities/possessions mentioned in the character sheets (e.g. a
# named pet or place), so the retrieval pool surfaces those continuity details.
def build_retrieval_query(section: Section, characters: list[Character]) -> str:
    names = [c.name for c in characters]
    entities = extract_scene_entities(characters)
    tail = ", ".join(dict.fromkeys(names + entities))  # de-dupe, keep order
    return f"{section.goal}\n{section.key_events}\n{tail}"


# ##################################################################
# extract scene entities (#11)
# pull proper-noun entities (named pets, places, objects, second names) out of
# the character biographies and traits, excluding the character names themselves
# and a small stop set. Heuristic and cheap — no model call.
def extract_scene_entities(characters: list[Character]) -> list[str]:
    known = {c.name.lower() for c in characters}
    # also treat each word of a multi-word character name as "known"
    for c in characters:
        for w in c.name.split():
            known.add(w.lower())
    found: list[str] = []
    seen: set[str] = set()
    for c in characters:
        blob = " ".join([c.biography or ""] + list(c.traits or []))
        for m in _PROPER_RE.finditer(blob):
            word = m.group(1)
            low = word.lower()
            if low in known or low in _STOPWORDS or low in seen:
                continue
            seen.add(low)
            found.append(word)
    return found


# ##################################################################
# similarity / near-duplicate (#16)
# word-level SequenceMatcher ratio in [0, 1] (mirrors analyze_novel.similarity).
def _similarity(a: str, b: str) -> float:
    ta = [w.lower() for w in _WORD_RE.findall(a)]
    tb = [w.lower() for w in _WORD_RE.findall(b)]
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return SequenceMatcher(None, ta, tb, autojunk=False).ratio()


# pure decision function so the retry logic is testable without a model call.
def is_near_duplicate(new_text: str, prev_text: str, threshold: float = DEDUP_THRESHOLD) -> bool:
    if not new_text or not prev_text:
        return False
    return _similarity(new_text, prev_text) >= threshold


# ##################################################################
# overused ngrams (#38)
# distinctive (non-all-stopword) 3+word phrases in the section that already
# appear >= threshold times across the manuscript so far.
def overused_ngrams(section_text: str, manuscript_text: str, threshold: int = NGRAM_REPEAT_THRESHOLD,
                    n: int = 3, limit: int = 10) -> list[str]:
    if not manuscript_text.strip():
        return []
    man_tokens = [w.lower() for w in _WORD_RE.findall(manuscript_text)]
    if len(man_tokens) < n:
        return []
    man_grams = [" ".join(man_tokens[i:i + n]) for i in range(len(man_tokens) - n + 1)]
    from collections import Counter
    man_counts = Counter(man_grams)

    sec_tokens = [w.lower() for w in _WORD_RE.findall(section_text)]
    flagged: list[str] = []
    seen: set[str] = set()
    for i in range(len(sec_tokens) - n + 1):
        gram_words = sec_tokens[i:i + n]
        if all(w in _STOPWORDS for w in gram_words):
            continue
        gram = " ".join(gram_words)
        if gram in seen:
            continue
        if man_counts.get(gram, 0) >= threshold:
            seen.add(gram)
            flagged.append(gram)
            if len(flagged) >= limit:
                break
    return flagged


# ##################################################################
# last sentences (#65)
# the literal last `count` sentences of a passage, for the transition recap.
def last_sentences(text: str, count: int = 3) -> str:
    collapsed = re.sub(r"\s+", " ", (text or "").strip())
    if not collapsed:
        return ""
    parts = [p.strip() for p in _SENT_SPLIT_RE.split(collapsed) if p.strip()]
    if not parts:
        return ""
    return " ".join(parts[-count:])


# ##################################################################
# find dropped beats (#30)
# cheap keyword heuristic: for each planned beat in key_events (and the goal),
# check whether most of its content words appear in the prose. Beats whose
# content is largely absent are flagged as possibly dropped. Never blocks.
def find_dropped_beats(section: Section, prose: str) -> list[str]:
    prose_words = {w.lower() for w in _WORD_RE.findall(prose)}
    dropped: list[str] = []
    for beat in _split_beats(section.key_events):
        content = [w.lower() for w in _WORD_RE.findall(beat)
                   if len(w) > 3 and w.lower() not in _STOPWORDS]
        if len(content) < 2:
            continue
        present = sum(1 for w in content if w in prose_words)
        if present / len(content) < 0.34:
            dropped.append(beat.strip())
    return dropped


# ##################################################################
# semantic beat confirmation (#94)
# the keyword prefilter above cannot tell a genuinely dropped beat from a
# paraphrased one ("abandons the maps, trusting Biscuit's nose" rendered as
# "she folded the useless survey and let the dog lead" shares zero keywords),
# so with multi-plot chapters it over-flags and the revision pass chases
# noise. For the (usually few) suspects the prefilter raises, ONE cheap
# FAST-tier structured call asks whether each beat's dramatic content actually
# occurs in the prose, even paraphrased. Costs nothing when nothing is
# flagged; on any error or a malformed reply it falls back to the unfiltered
# suspect list (never lose a real drop to a flaky check, never crash a run).
class _BeatCheck(BaseModel):
    beat: str = Field(description="The planned beat, verbatim as given")
    dramatized: bool = Field(description="True if this beat's events actually happen in the prose, even reworded, renamed, or paraphrased")


class _BeatChecks(BaseModel):
    checks: list[_BeatCheck] = Field(default_factory=list, description="One verdict per beat, in the order given")


_MAX_BEAT_SUSPECTS = 8


def _reconcile_beat_checks(suspects: list[str], checks: list) -> list[str]:
    # pure mapping: keep every suspect the model did NOT positively confirm as
    # dramatized. Verdicts are matched by position; a count mismatch keeps the
    # unmatched tail (conservative — a lost real drop is worse than a spurious
    # weave-in request).
    if len(checks) != len(suspects):
        checks = list(checks)[:len(suspects)]
    kept: list[str] = []
    for i, suspect in enumerate(suspects):
        if i < len(checks) and getattr(checks[i], "dramatized", False):
            continue
        kept.append(suspect)
    return kept


def confirm_dropped_beats(section_text: str, suspects: list[str]) -> list[str]:
    if not suspects:
        return []
    suspects = suspects[:_MAX_BEAT_SUSPECTS]
    numbered = "\n".join(f"{i + 1}. {b}" for i, b in enumerate(suspects))
    messages = [
        {"role": "system", "content": (
            "You are a continuity checker. For each planned story beat, decide whether "
            "its dramatic content actually OCCURS in the prose — count it as dramatized "
            "if the events happen even reworded, renamed, compressed, or paraphrased. "
            "Only mark a beat NOT dramatized when its substance is genuinely absent."
        )},
        {"role": "user", "content": (
            f"PROSE:\n{section_text}\n\nPLANNED BEATS:\n{numbered}\n\n"
            "Return one verdict per beat, in order."
        )},
    ]
    try:
        result = chat_structured(messages, _BeatChecks)
        return _reconcile_beat_checks(suspects, result.checks)
    except Exception:
        return suspects


def _split_beats(key_events: str) -> list[str]:
    if not key_events:
        return []
    parts = re.split(r"[;\n]|(?<=[.!?])\s+", key_events)
    return [p.strip() for p in parts if len(p.strip()) > 8]


# ##################################################################
# render canon block (#2/#27)
# ask the ledger for the authoritative facts about the scene's entities and
# format them as the CANON FACTS block. No-op when no ledger is available.
def _render_canon_block(ledger, character_names: list[str], scene_entities: list[str]) -> str:
    if ledger is None or not hasattr(ledger, "get_canon_facts"):
        return ""
    entities = list(dict.fromkeys(character_names + scene_entities))
    try:
        facts = ledger.get_canon_facts(entities)
    except Exception:
        return ""
    if not isinstance(facts, dict):
        return ""
    return render_canon_facts(facts)


# ##################################################################
# extract facts (#76)
# run the ledger's extraction over the finished prose and coerce the result into
# a list[Fact] for SectionResult.new_facts. No-op ([]) without a ledger.
def _extract_facts(ledger, text: str, known_entities: list[str], section_id: str) -> list[Fact]:
    if ledger is None or not hasattr(ledger, "extract_facts"):
        return []
    try:
        raw = ledger.extract_facts(text, list(dict.fromkeys(known_entities)))
    except Exception:
        return []
    facts: list[Fact] = []
    for entry in raw or []:
        if isinstance(entry, Fact):
            facts.append(entry if entry.first_seen
                         else entry.model_copy(update={"first_seen": section_id}))
            continue
        # fact_ledger.ExtractedFact uses `entity`; models.Fact uses `subject`.
        if isinstance(entry, dict):
            subject = entry.get("subject") or entry.get("entity") or ""
            attribute = entry.get("attribute", "")
            value = entry.get("value", "")
        else:
            subject = getattr(entry, "subject", "") or getattr(entry, "entity", "")
            attribute = getattr(entry, "attribute", "")
            value = getattr(entry, "value", "")
        subject, attribute, value = str(subject).strip(), str(attribute).strip(), str(value).strip()
        if not (subject and attribute and value):
            continue
        facts.append(Fact(subject=subject, attribute=attribute, value=value, first_seen=section_id))
    return facts


# ##################################################################
# continuity warnings log (#30/#38)
# append a non-blocking JSON record of any drift/repetition signals for a
# section. Best-effort — never raises into the pipeline.
def _log_continuity_warnings(novel_dir: Path | None, section_id: str,
                             dedup_warning: str | None, overused: list[str],
                             dropped_beats: list[str]) -> None:
    if novel_dir is None:
        return
    if not (dedup_warning or overused or dropped_beats):
        return
    entry: dict[str, str | list[str]] = {"section": section_id}
    if dedup_warning:
        entry["near_duplicate"] = dedup_warning
    if overused:
        entry["overused_phrases"] = overused
    if dropped_beats:
        entry["possibly_dropped_beats"] = dropped_beats
    try:
        path = Path(novel_dir) / CONTINUITY_WARNINGS_FILE
        existing: list = []
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    existing = loaded
            except (json.JSONDecodeError, OSError):
                existing = []
        # replace any prior entry for the same section (idempotent on rewrite)
        existing = [e for e in existing if not (isinstance(e, dict) and e.get("section") == section_id)]
        existing.append(entry)
        path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        return


# ##################################################################
# summarize chapter (#14)
# produce a compact (a few sentences) summary of a completed chapter's prose,
# for use as long-term memory in later chapters. Uses the default (cheap) tier.
def summarize_chapter(chapter: Chapter, chapter_text: str) -> str:
    text = chapter_text.strip()
    if not text:
        return ""
    window = text[-12000:]
    system_content = (
        "You compress a chapter of a novel into a compact continuity summary for the "
        "author to keep later chapters consistent. Output 3-5 plain sentences covering: "
        "what changed in the plot, the current situation of the main characters, and any "
        "new facts (places, objects, relationships) established. No preamble, no bullet "
        "points, no commentary — just the summary sentences."
    )
    user_content = (
        f"CHAPTER {chapter.number}: {chapter.title}\n"
        f"Chapter goal: {chapter.chapter_goal}\n\n"
        f"CHAPTER PROSE (end of chapter shown):\n{window}\n\n"
        "Write the compact 3-5 sentence continuity summary now."
    )
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
    return _postprocess(chat(messages, max_tokens=400)).strip()


# ##################################################################
# render helpers
def _render_scene_directive(section: Section) -> str:
    stype = (section.scene_type or "scene").strip().lower()
    if stype == "sequel":
        body = (
            "This is a SEQUEL (reactive). Move through the POV character's emotional REACTION "
            "to the previous setback, a DILEMMA of bad options, and a DECISION that commits them "
            "to a new goal."
        )
    else:
        body = (
            "This is a SCENE (proactive). The POV character pursues a concrete GOAL, meets "
            "escalating CONFLICT, and ends on a DISASTER that leaves them worse off."
        )
    if section.disaster:
        body += f" The turn this section builds toward: {section.disaster}"
    return f"\n\nSECTION DRAMATIC SHAPE: {body}\n"


def _render_characters(characters: list[Character]) -> str:
    if not characters:
        return "(none defined)"
    lines = []
    for c in characters:
        traits = ", ".join(c.traits) if c.traits else ""
        trait_part = f" — {traits}" if traits else ""
        lines.append(f"- {c.name} ({c.role.value if hasattr(c.role, 'value') else c.role}): {c.biography}{trait_part}")
    return "\n".join(lines)


def _render_voices(characters: list[Character]) -> str:
    lines = [render_character_voice(c) for c in characters]
    lines = [ln for ln in lines if ln]
    if not lines:
        return ""
    body = "\n".join(f"- {ln}" for ln in lines)
    return (
        "\n\nCHARACTER VOICES (write each character's dialogue in their own distinct voice — "
        "keep these registers, rhythms, and verbal tics consistent):\n" + body + "\n"
    )


def _render_established(sentences: list[str]) -> str:
    if not sentences:
        return ""
    bullets = "\n".join(f"- {s}" for s in sentences)
    return (
        "\n\nESTABLISHED DETAILS (drawn from earlier in this same novel — keep your prose "
        "consistent with these; do not contradict them):\n"
        f"{bullets}\n"
    )


def _render_pov_tense(writing_style: WritingStyle) -> str:
    bits = []
    pov = (getattr(writing_style, "pov", "") or "").strip()
    tense = (getattr(writing_style, "tense", "") or "").strip()
    if pov:
        bits.append(f"POINT OF VIEW: {pov}")
    if tense:
        bits.append(f"TENSE: {tense}")
    if not bits:
        return ""
    return "\n" + " — ".join(bits) + " (hold this POV and tense consistently throughout).\n"


# ##################################################################
# generate prose
# build the system + user prompt from the shared context and call the model on
# the escalated PROSE_TIER (#46) by default. extra_instruction lets a retry
# append a directive so it becomes a genuinely fresh (non-cached) generation;
# tier lets the meta-commentary fallback (#91) drop to the reliable
# non-reasoning TIER for its final attempt.
def _generate_prose(ctx: _PromptContext, extra_instruction: str, tier: Tier = PROSE_TIER) -> str:
    ws = ctx.writing_style
    system_content = f"""You are a novelist writing prose fiction. You output ONLY narrative text - no commentary, no meta-discussion, no preamble, no "I'll write..." statements. Just the story itself.

Writing Style: {ws.style_description}
Tone: {ws.tone}
Voice: {ws.voice}
Pacing: {ws.pacing}{ctx.pov_tense}

NOVEL STRUCTURE:
{ctx.all_chapters_summary}

{ctx.position_note}

CAST (use these exact names and keep each character consistent with their description):
{ctx.character_block}{ctx.engine_block}{ctx.voice_block}

{PROSE_CRAFT}

CRITICAL: Output ONLY the narrative prose. No introductions, no explanations, no section headers. Start immediately with the story text."""

    user_content = f"""CHAPTER: {ctx.chapter.number} - {ctx.chapter.title}
Chapter Goal: {ctx.chapter.chapter_goal}
Chapter Opening: {ctx.chapter.opening_situation}
Chapter Closing: {ctx.chapter.closing_situation}

SECTION: {ctx.section.number}
Section Goal: {ctx.section.goal}
Key Events: {ctx.section.key_events}{ctx.scene_directive}{ctx.plot_block}{ctx.arc_block}{ctx.canon_block}{ctx.roster_block}{ctx.summary_block}{ctx.established_block}{ctx.recap_block}{ctx.previous_context}

Write approximately {ctx.word_lo}-{ctx.word_hi} words of narrative prose for this section.
Maintain continuity with the cast, the CANON FACTS (which are fixed), the established details, and the previous text.
Apply the craft rules above: microtension, show-don't-name, subjective description, sentence-length pacing, and cut the listed prose pitfalls.
Output ONLY the story text. No headers, no commentary, no meta-text. Begin the narrative immediately.{extra_instruction}"""

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
    # #95 — cache guard: never cache (and never trust a cached) response that
    # is planning notes or a truncation. Without this, one bad generation
    # poisons brain.py's content-hash cache and every resume replays it.
    return chat(messages, max_tokens=2400, tier=tier,
                validate=lambda raw: _invalid_prose_reason(_postprocess(raw), ctx.word_lo) is None)


# ##################################################################
# revise prose (#36)
# one bounded critique-and-line-edit pass. Requests TARGETED edits against a
# short rubric (show-vs-tell, voice distinctness, cliché density, hook strength)
# plus the specific over-used phrases and dropped beats — never a full rewrite
# of the scene's existing content, but restoring a missing planned beat
# necessarily means ADDING material, so that exception is stated explicitly
# rather than left to collide with the general "don't change events" rule (an
# earlier version of this prompt banned changing events unconditionally, which
# silently defeated the dropped-beats weave-in instruction below it — measured
# on a real test novel: beats stayed missing after the pass every time).
def _revise_prose(draft: str, overused: list[str],
                  dropped_beats: list[str]) -> str:
    notes = []
    if overused:
        notes.append("Replace these over-used phrases with fresh, specific images: "
                     + "; ".join(overused) + ".")
    if dropped_beats:
        notes.append(
            "These planned beats are MISSING from the draft — you MUST add the material "
            "needed to include them (new sentences or a short new paragraph, inserted where "
            "they fit the scene's flow), not merely reword existing text: "
            + "; ".join(dropped_beats) + "."
        )
    extra_notes = ("\n" + "\n".join(notes)) if notes else ""

    events_rule = (
        "You do NOT rewrite the scene wholesale or discard its existing events — preserve "
        "the plot, POV, and structure of what's already there."
        if not dropped_beats else
        "You do NOT rewrite the scene wholesale or discard any of its existing events — "
        "preserve the plot, POV, and structure of what's already there. The one exception: "
        "the MISSING PLANNED BEATS listed below must be added, even though that means the "
        "section will grow — that addition is required, not optional polish."
    )
    system_content = (
        "You are a line editor improving a draft section of a novel. You make TARGETED "
        f"edits only — {events_rule} Output ONLY the edited prose, no commentary.\n\n"
        + PROSE_CRAFT
    )
    user_content = (
        "Edit the draft below against this rubric, changing only what needs changing:\n"
        "- SHOW don't TELL: convert any named emotion into concrete sensory detail.\n"
        "- VOICE: make each character's dialogue sound distinct.\n"
        "- CLICHÉ: remove banned/stock phrases and clichés (see the craft rules above).\n"
        "- HOOK: sharpen the opening line and the closing beat.\n"
        f"{extra_notes}\n\n"
        f"DRAFT:\n{draft}\n\n"
        "Output the edited section prose now, and nothing else."
    )
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
    # #95 — same cache guard as _generate_prose: a revised section must still
    # be prose, not planning notes; use half the draft's length as the floor
    # (a line-edit shouldn't shrink the section drastically).
    floor = max(1, len(draft.split()) // 2)
    return chat(messages, max_tokens=2400, tier=PROSE_TIER,
                validate=lambda raw: _invalid_prose_reason(_postprocess(raw), floor) is None)


# ##################################################################
# postprocess
# strip any reasoning/think-tag preamble (PROSE_TIER runs in reasoning mode) and
# then drop leading meta lines. Idempotent for plain (non-thinking) output.
def _postprocess(text: str) -> str:
    return _clean_narrative(_strip_think(text))


def _strip_think(text: str) -> str:
    if not text:
        return text
    # remove any well-formed <think>...</think> / <thinking>...</thinking> blocks
    cleaned = _THINK_RE.sub("", text)
    # handle a dangling closing tag with no matching opener (reasoning preamble
    # emitted before an unterminated-looking tag): keep the prose after it.
    lower = cleaned.lower()
    best = -1
    best_tag = ""
    for tag in ("</think>", "</thinking>", "</reasoning>"):
        idx = lower.rfind(tag)
        if idx > best:
            best = idx
            best_tag = tag
    if best != -1:
        tail = cleaned[best + len(best_tag):]
        if tail.strip():
            cleaned = tail
    return cleaned.strip()


def _clean_narrative(text: str) -> str:
    lines = text.split("\n")
    skip_prefixes = ("i'll ", "i will ", "here's ", "here is ", "continuing ", "let me ")
    cleaned = []
    skipping = True
    for line in lines:
        lower = line.strip().lower()
        if skipping and (not lower or any(lower.startswith(p) for p in skip_prefixes)):
            continue
        skipping = False
        cleaned.append(line)
    return "\n".join(cleaned) if cleaned else text


# ##################################################################
# looks like meta commentary (#91)
# detect a response that is the model's own planning/analysis notes rather
# than a story: a numbered, bold-headed breakdown, or prompt-label markers
# ("POV/Tense:", "Canon Facts:", ...) appearing early in the text. Checked
# against the postprocessed text (after _strip_think already ran), since this
# catches the case where the model never used a <think> wrapper at all.
def _looks_like_meta_commentary(text: str) -> bool:
    if not text:
        return False
    stripped = text.strip()
    if _NUMBERED_BOLD_HEADER_RE.match(stripped):
        return True
    head = stripped[:800].lower()
    return any(marker in head for marker in _META_MARKERS)


# characters a genuinely finished scene may end on: standard sentence-enders,
# a closing quote/paren after one, or an intentional dramatic trail-off
# (em-dash / ellipsis are common deliberate cliffhanger endings in fiction).
_CLEAN_ENDING_CHARS = frozenset(".!?\"”’')—…")


# ##################################################################
# looks truncated (#93)
# detect a response that was cut off before finishing — either far short of
# the target length (the "thinking" budget on the reasoning tier occasionally
# crowds out the visible answer, leaving a short fragment), or one that
# reached a healthy length but still stops mid-clause on a comma/bare word at
# the very end. The length check uses a generous 50% floor against the
# section's own (already-adaptive) word-count lower bound so this never flags
# a legitimately short "fast" scene.
def _looks_truncated(text: str, word_lo: int) -> bool:
    if not text or not text.strip():
        return True
    stripped = text.strip()
    if len(stripped.split()) < word_lo * 0.5:
        return True
    return stripped[-1] not in _CLEAN_ENDING_CHARS


# ##################################################################
# invalid prose reason (#91/#93)
# combined check run after every draft/retry: returns a human-readable defect
# description if `text` isn't usable prose, else None.
def _invalid_prose_reason(text: str, word_lo: int) -> str | None:
    if _looks_like_meta_commentary(text):
        return "model returned planning/analysis notes instead of prose"
    if _looks_truncated(text, word_lo):
        return (
            f"response was truncated at {len(text.split())} words, far short of the "
            f"{word_lo}-word target floor"
        )
    return None
