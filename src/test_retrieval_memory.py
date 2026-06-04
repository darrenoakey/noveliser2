"""Real tests for the retrieval memory. No mocks — uses the live embedding
backend. Embedding/relevance tests skip cleanly if the backend is unreachable."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from retrieval_memory import RetrievalMemory, _cosine, split_sentences  # noqa: E402


def _embeddings_available() -> bool:
    try:
        import asyncio

        from daz_agent_sdk import agent
        r = asyncio.run(agent.embed(["probe"]))
        return bool(r.embeddings)
    except Exception:
        return False


EMBED_OK = _embeddings_available()
skip_if_no_embed = pytest.mark.skipif(not EMBED_OK, reason="embedding backend unreachable")


def test_split_sentences_filters_and_caps():
    text = "Jeff opened the blue door slowly. He nodded. The dog was a golden retriever named Max."
    sents = split_sentences(text)
    # "He nodded." is too short and is dropped
    assert any("blue door" in s for s in sents)
    assert any("golden retriever" in s for s in sents)
    assert all(len(s) <= 400 for s in sents)
    assert not any(s.strip() == "He nodded." for s in sents)


def test_cosine_identity_and_orthogonal():
    assert _cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert _cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


@skip_if_no_embed
def test_ensure_section_is_idempotent():
    mem = RetrievalMemory()
    n1 = mem.ensure_section("ch1.s1", "Clara Whitby lived in a lighthouse. The sea was grey and endless.")
    assert n1 >= 1
    n2 = mem.ensure_section("ch1.s1", "different text but same id")
    assert n2 == 0  # already present -> not re-embedded
    assert "ch1.s1" in mem


@skip_if_no_embed
def test_retrieval_finds_relevant_sentence():
    mem = RetrievalMemory()
    mem.ensure_section("ch1.s1", (
        "Jeff drove a battered red pickup truck. "
        "The kitchen smelled of burnt toast every morning. "
        "Clara kept a telescope on the lighthouse balcony."
    ))
    hits = mem.retrieve("What vehicle does Jeff own?", k=1)
    assert hits
    assert "pickup truck" in hits[0].lower()


@skip_if_no_embed
def test_save_and_load_roundtrip(tmp_path):
    mem = RetrievalMemory()
    mem.ensure_section("ch1.s1", "Jeff drove a battered red pickup truck across the desert.")
    path = tmp_path / "mem.json"
    mem.save(path)
    loaded = RetrievalMemory.load(path)
    assert len(loaded) == len(mem)
    assert "ch1.s1" in loaded
    hits = loaded.retrieve("Jeff's truck", k=1)
    assert hits and "pickup truck" in hits[0].lower()


@skip_if_no_embed
def test_retrieve_excludes_named_section():
    mem = RetrievalMemory()
    mem.ensure_section("ch2.s1", "Jeff drove a battered red pickup truck across the desert.")
    assert mem.retrieve("Jeff truck", k=5, exclude_section="ch2.s1") == []
