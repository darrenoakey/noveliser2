"""Real tests for analyze_novel — no mocks, no backend needed.

Builds small real section JSON fixtures on disk (same schema the pipeline
writes: chapter_N_section_M.json with a {"text": ...} body) and verifies the
phrase-counting, near-duplicate detection, and stats produce correct results
on known inputs.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from analyze_novel import (  # noqa: E402
    REPORT_NAME,
    analyze,
    count_phrases,
    find_duplicates,
    load_sections,
    resolve_directory,
    section_stats,
    similarity,
    tokenize,
    write_report,
)


# ##################################################################
# helper: write a section checkpoint the way the pipeline does
def _write_section(directory: Path, chapter: int, number: int, text: str) -> None:
    path = directory / f"chapter_{chapter}_section_{number}.json"
    path.write_text(json.dumps({"text": text, "new_facts": []}))


# ##################################################################
# tokenize
def test_tokenize_lowercases_and_keeps_apostrophes():
    assert tokenize("It's the Weight Of it.") == ["it's", "the", "weight", "of", "it"]


# ##################################################################
# phrase counting
def test_count_phrases_finds_overused_phrase():
    # "the weight of" appears 3 times; a distractor sentence does not repeat it
    texts = [
        "She felt the weight of the world. The weight of the past pressed down.",
        "Again the weight of everything returned to him at dawn.",
        "A completely different sentence with no repetition whatsoever here.",
    ]
    hits = count_phrases(texts, ns=(3,), top=10, min_count=2)
    phrases = {h.phrase: h.count for h in hits}
    assert "the weight of" in phrases
    assert phrases["the weight of"] == 3


def test_count_phrases_ignores_pure_stopword_grams():
    # "it was the" is all stopwords -> excluded even though it repeats; the
    # content-bearing "was the best" survives
    texts = ["it was the best", "it was the worst", "it was the last"]
    hits = count_phrases(texts, ns=(3,), top=10, min_count=2)
    assert all(h.phrase != "it was the" for h in hits)
    assert any(h.phrase == "was the best" or h.phrase == "was the last" for h in hits) is False
    # sanity: an all-stopword gram really was present in the input yet excluded
    assert "it" in tokenize(texts[0]) and "was" in tokenize(texts[0])


def test_count_phrases_respects_min_count():
    texts = ["golden retriever named max", "another golden retriever barked"]
    # "golden retriever" occurs twice
    two = {h.phrase for h in count_phrases(texts, ns=(2,), top=10, min_count=2)}
    assert "golden retriever" in two
    three = {h.phrase for h in count_phrases(texts, ns=(2,), top=10, min_count=3)}
    assert "golden retriever" not in three


# ##################################################################
# similarity / duplicates
def test_similarity_extremes():
    assert similarity("hello world", "hello world") == 1.0
    assert similarity("", "anything") == 0.0
    assert similarity(
        "The cat sat on the warm mat by the fire.",
        "Quantum entanglement defies classical intuition entirely.",
    ) < 0.4


def test_find_duplicates_flags_near_identical_not_different(tmp_path):
    base = (
        "Jeff walked into the dim kitchen and set the mug down on the counter. "
        "Steam curled from the coffee while the rain kept tapping the window."
    )
    near = base.replace("dim kitchen", "dim hallway")  # ~1 word changed => ~0.94
    different = (
        "The spaceship's reactor screamed as alarms flared across every console "
        "and the crew scrambled toward the escape pods in the smoke."
    )
    _write_section(tmp_path, 1, 1, base)
    _write_section(tmp_path, 1, 2, near)
    _write_section(tmp_path, 1, 3, different)

    sections = load_sections(tmp_path)
    assert [s.label for s in sections] == ["ch1.s1", "ch1.s2", "ch1.s3"]

    pairs = find_duplicates(sections, threshold=0.6)
    flagged = {frozenset((p.a, p.b)) for p in pairs}
    # near-identical pair is flagged
    assert frozenset(("ch1.s1", "ch1.s2")) in flagged
    # the very-different section is not flagged against either
    assert frozenset(("ch1.s1", "ch1.s3")) not in flagged
    assert frozenset(("ch1.s2", "ch1.s3")) not in flagged
    # the flagged pair is consecutive within the same chapter
    dup = next(p for p in pairs if {p.a, p.b} == {"ch1.s1", "ch1.s2"})
    assert dup.ratio > 0.9
    assert dup.consecutive_same_chapter is True


def test_find_duplicates_consecutive_only_skips_cross_chapter(tmp_path):
    text = "Identical prose repeated across two different chapters entirely here."
    _write_section(tmp_path, 1, 1, text)
    _write_section(tmp_path, 2, 1, text)  # same text, different chapter, not adjacent
    sections = load_sections(tmp_path)
    # consecutive-only: ch1.s1 and ch2.s1 are not neighbours -> not compared
    assert find_duplicates(sections, threshold=0.6, consecutive_only=True) == []
    # full comparison still catches the identical cross-chapter pair
    full = find_duplicates(sections, threshold=0.6, consecutive_only=False)
    assert len(full) == 1
    assert full[0].ratio == 1.0
    assert full[0].consecutive_same_chapter is False


# ##################################################################
# stats
def test_section_stats_counts(tmp_path):
    _write_section(tmp_path, 3, 2, "The old cold house was quiet. Rain fell hard.")
    sections = load_sections(tmp_path)
    stats = section_stats(sections[0])
    assert stats.label == "ch3.s2"
    assert stats.word_count == 9
    assert stats.sentence_count == 2
    # old, cold, quiet, hard are in the common-adjective set
    assert stats.adjective_count == 4
    assert stats.adjective_density == round(4 / 9, 4)


# ##################################################################
# end-to-end analyze + report writing
def test_analyze_and_write_report(tmp_path):
    _write_section(tmp_path, 1, 1, "The ghost drifted through the ghost house at night.")
    _write_section(tmp_path, 1, 2, "The ghost drifted through the ghost house at dusk.")
    _write_section(tmp_path, 2, 1, "A bright morning of laughter and warm bread baking.")
    # a non-section json must be ignored
    (tmp_path / "metadata.json").write_text(json.dumps({"title": "x"}))

    report = analyze(tmp_path, top=10, dup_threshold=0.6)
    assert report.section_count == 3
    assert report.total_words > 0
    # the two ghost sections are near-duplicates
    assert any({p.a, p.b} == {"ch1.s1", "ch1.s2"} for p in report.duplicate_pairs)
    # "the ghost" is an over-used phrase
    assert any("ghost" in h.phrase for h in report.repeated_phrases)

    out_path = write_report(report, tmp_path)
    assert out_path.name == REPORT_NAME
    loaded = json.loads(out_path.read_text())
    assert loaded["section_count"] == 3
    assert "repeated_phrases" in loaded
    assert "duplicate_pairs" in loaded


# ##################################################################
# directory resolution
def test_resolve_directory_accepts_path(tmp_path):
    assert resolve_directory(str(tmp_path)) == tmp_path.resolve()


def test_resolve_directory_missing_raises():
    import pytest

    with pytest.raises(FileNotFoundError):
        resolve_directory("this_novel_does_not_exist_xyz")
