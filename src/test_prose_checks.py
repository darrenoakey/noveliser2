from pathlib import Path

from prose_checks import (
    LIMITS,
    analyse_prose,
    find_contrasts,
    find_moral_endings,
    find_same_openings,
    find_triads,
    sentence_length_spread,
    split_sentences,
)

SAMPLES = Path(__file__).parent / "style_samples"


# ##################################################################
# read samples
# every calibration sample whose file name starts with the prefix
def _read_samples(prefix: str) -> list[tuple[str, str]]:
    return [(p.name, p.read_text(encoding="utf-8")) for p in sorted(SAMPLES.rglob(f"{prefix}*.txt"))]


# ##################################################################
# human fiction stays below the review triggers
# published novels must not be sent for revision on anything except the one
# dash-heavy Fitzgerald passage; em dashes are a period style there.
def test_human_fiction_rarely_trips_review():
    samples = _read_samples("human_")
    assert len(samples) == 15
    tripped = {name: [f.kind for f in analyse_prose(text).tripped()] for name, text in samples}
    non_dash = {name: kinds for name, kinds in tripped.items() if set(kinds) - {"em_dash"}}
    assert non_dash == {}
    assert sum(1 for kinds in tripped.values() if kinds) <= 1


# ##################################################################
# earlier generated scenes trip review
# the old prompt set's scenes lean on the counted devices; most must trip
def test_generated_scenes_trip_review():
    samples = _read_samples("model_")
    assert len(samples) == 10
    reports = [analyse_prose(text) for _, text in samples]
    assert sum(r.needs_revision for r in reports) >= 8
    assert all(r.excess() > 0 for r in reports if r.needs_revision)


# ##################################################################
# triad detection
def test_triads_count_short_series_and_staccato_not_long_clauses():
    hits = find_triads(
        split_sentences(
            "The generator came on, uneven, labored, but steady. "
            "He turned to the door, found his coat and hat under the gas-light, and plunged out into the night. "
            "He ran. He fell. He rose."
        )
    )
    assert any("uneven, labored, but steady" in h for h in hits)
    assert any(h == "He ran. He fell. He rose." for h in hits)
    assert not any("plunged out" in h for h in hits)


# ##################################################################
# contrast framing
def test_contrasts_find_both_forms():
    hits = find_contrasts(
        [
            "It was not courage that kept him at the door, but love.",
            "It wasn't fear. It was something older.",
            "She bought bread and went home.",
        ]
    )
    assert len(hits) == 2


# ##################################################################
# moral endings only count paragraph-final narration
def test_moral_endings():
    paragraphs = [
        "They crossed the yard. At the last step she took his hand. Maybe that was enough.",
        "Maybe that was enough. She went in and shut the door.",
        '"Maybe that was enough," she said. "It was."',
    ]
    assert find_moral_endings(paragraphs) == ["Maybe that was enough."]


# ##################################################################
# same openings count runs of three
def test_same_openings():
    sentences = split_sentences("She stood. She waited. She left. He stayed. He slept.")
    assert find_same_openings(sentences) == ["She stood. She waited. She left."]


# ##################################################################
# therapy language counts only in dialogue
def test_therapy_language_is_dialogue_only():
    narration = "The counsellor's leaflet said: I hear you, and your feelings are valid."
    assert analyse_prose(narration, dialogue_lines=[]).findings["therapy_dialogue"].count == 0
    dialogue = ["I hear you.", "That's valid, and you don't have to carry this alone.", "Pass the salt."]
    finding = analyse_prose(narration, dialogue_lines=dialogue).findings["therapy_dialogue"]
    assert finding.count == 3
    assert finding.examples[0] == "I hear you."


# ##################################################################
# brief quotes the scene's own sentences and the allowed count
def test_brief_quotes_examples():
    text = "\n".join(["It wasn't fear. It was hunger. She ate. Not because she wanted to, but because she must."] * 6)
    report = analyse_prose(text)
    assert report.needs_revision
    brief = report.brief()
    assert '"It wasn\'t fear. It was' in brief
    assert "At most" in brief
    assert "OVER" in report.summary()


# ##################################################################
# a single use in a short scene never trips
def test_single_use_never_trips():
    report = analyse_prose("It was not the money but the silence that worried her. She counted the jars twice.")
    assert not report.needs_revision
    assert all(limit.floor >= 1 for limit in LIMITS.values())


# ##################################################################
# sentence length spread
def test_sentence_length_spread():
    assert sentence_length_spread(["One two three.", "One two three."]) == 0.0
    assert sentence_length_spread(["One.", "One two three four five six seven."]) > 0.5
    assert sentence_length_spread([]) == 0.0
