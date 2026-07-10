"""Real tests for craft.py prompt helpers and the new model fields. Pure
string/logic — no backend, no mocks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from craft import (  # noqa: E402
    PROSE_CRAFT,
    render_canon_facts,
    render_character_voice,
    render_name_roster,
    word_target_for_scene,
)
from models import Character, CharacterRole, Section, WritingStyle  # noqa: E402


# ##################################################################
# #37 — banned-phrase list
def test_prose_craft_bans_measured_phrases():
    lowered = PROSE_CRAFT.lower()
    for phrase in ("the weight of", "ghost", "breath hitched", "eyes were"):
        assert phrase in lowered, f"expected banned phrase {phrase!r} in PROSE_CRAFT"


# ##################################################################
# #39 — voice fingerprint model fields default (old checkpoints load)
def test_character_voice_fields_default_empty():
    c = Character(name="Mara", biography="b", role=CharacterRole.PROTAGONIST, traits=["bold"])
    assert c.voice_register == ""
    assert c.sentence_style == ""
    assert c.verbal_tic == ""


def test_render_character_voice_formats_set_fields():
    c = Character(
        name="Mara",
        biography="b",
        role=CharacterRole.PROTAGONIST,
        traits=["bold"],
        voice_register="terse working-class slang",
        sentence_style="clipped one-liners",
        verbal_tic="always ends with 'right?'",
    )
    out = render_character_voice(c)
    assert out.startswith("Mara — ")
    assert "terse working-class slang" in out
    assert "clipped one-liners" in out
    assert "right?" in out


def test_render_character_voice_empty_when_no_fields():
    c = Character(name="Mara", biography="b", role=CharacterRole.MINOR, traits=[])
    assert render_character_voice(c) == ""


def test_render_character_voice_partial_fields():
    c = Character(
        name="Ida",
        biography="b",
        role=CharacterRole.SUPPORTING,
        traits=[],
        verbal_tic="over-apologizes",
    )
    out = render_character_voice(c)
    assert "Ida — " in out
    assert "over-apologizes" in out
    assert "register" not in out


# ##################################################################
# #41 — adaptive word-count target
def test_section_intensity_defaults_medium():
    s = Section(number=1, goal="g", key_events="e")
    assert s.intensity == "medium"


def test_word_target_fast_is_shorter_than_slow():
    fast = Section(number=1, goal="g", key_events="e", intensity="fast")
    slow = Section(number=1, goal="g", key_events="e", intensity="slow")
    lo_f, hi_f = word_target_for_scene(fast)
    lo_s, hi_s = word_target_for_scene(slow)
    assert hi_f < lo_s, "fast scene ceiling should be below slow scene floor"
    assert lo_f < hi_f and lo_s < hi_s


def test_word_target_medium_and_scene_type_fallback():
    med = Section(number=1, goal="g", key_events="e", intensity="medium")
    assert word_target_for_scene(med) in {(1400, 1900), (1500, 2000), (1700, 2200)}
    sequel = Section(number=1, goal="g", key_events="e", intensity="medium", scene_type="sequel")
    lo_seq, _ = word_target_for_scene(sequel)
    scene = Section(number=1, goal="g", key_events="e", intensity="medium", scene_type="scene")
    lo_sc, _ = word_target_for_scene(scene)
    assert lo_seq >= lo_sc, "sequels should target at least as long as scenes"


def test_word_target_returns_int_tuple():
    s = Section(number=1, goal="g", key_events="e")
    r = word_target_for_scene(s)
    assert isinstance(r, tuple) and len(r) == 2
    assert all(isinstance(x, int) for x in r)


# ##################################################################
# #42 — structured POV/tense fields default
def test_writing_style_pov_tense_default_empty():
    ws = WritingStyle(
        style_description="s", tone="t", voice="v", pacing="p", examples=["ex"],
    )
    assert ws.pov == ""
    assert ws.tense == ""


def test_writing_style_pov_tense_set():
    ws = WritingStyle(
        style_description="s", tone="t", voice="v", pacing="p", examples=["ex"],
        pov="third limited", tense="past",
    )
    assert ws.pov == "third limited"
    assert ws.tense == "past"


# ##################################################################
# canon-facts + name-roster helpers
def test_render_canon_facts_formats_block():
    out = render_canon_facts({"Rex_breed": "beagle", "Elara_eye_color": "green"})
    assert "CANON FACTS" in out
    assert "Rex_breed: beagle" in out
    assert "Elara_eye_color: green" in out


def test_render_canon_facts_empty_dict():
    assert render_canon_facts({}) == ""


def test_render_canon_facts_skips_blank_values():
    out = render_canon_facts({"a": "x", "b": "   ", "c": ""})
    assert "a: x" in out
    assert "b:" not in out
    assert "c:" not in out


def test_render_name_roster_dedupes_and_formats():
    out = render_name_roster(["Elara", "Rex", "Elara", "", "  "])
    assert "NAME SPELLINGS" in out
    assert out.count("Elara") == 1
    assert "Rex" in out


def test_render_name_roster_empty():
    assert render_name_roster([]) == ""
    assert render_name_roster(["", "   "]) == ""
