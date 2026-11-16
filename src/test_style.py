import json
from pathlib import Path

import pytest

from agentd3_client import (
    Agentd3Error,
    create_subagent,
    get_conversation,
    run_to_completion,
)
from craft import (
    HOUSE_EXAMPLES,
    HOUSE_NARRATIVE_DISTANCE,
    PROSE_CRAFT,
    render_style_block,
)
from define_writing_style import enrich_writing_style, merge_styles
from models import (
    BookMetadata,
    CharactersList,
    CharacterVoice,
    SectionResult,
    WritingStyle,
)
from write_section import (
    _SYSTEM_TEMPLATE,
    TaggedScene,
    _build_scene_prompt,
    _clean_narrative,
    _example_speakers,
    _parse_tagged,
    _prose_from_lines,
    _revision_is_better,
    _scene_from_tagged,
    accepted_tail,
    build_revision_prompt,
    next_subagent_id,
    review_scene,
)

SAMPLES = Path(__file__).parent / "style_samples"


# ##################################################################
# legacy style
# a writing_style.json checkpoint written before the rich fields existed
def _legacy_style() -> WritingStyle:
    return WritingStyle(**json.loads((SAMPLES / "legacy_writing_style.json").read_text(encoding="utf-8")))


# ##################################################################
# legacy characters
def _legacy_characters():
    data = json.loads((SAMPLES / "legacy_characters.json").read_text(encoding="utf-8"))
    return CharactersList(**data).characters


# ##################################################################
# require daemon
# real integration tests need the local agentd3 daemon; skip cleanly without it
def _require_daemon() -> None:
    try:
        get_conversation("conv-0000000000000000")
    except Agentd3Error as err:
        if "connection error" in str(err):
            pytest.skip(f"agentd3 daemon unreachable: {err}")


# ##################################################################
# old checkpoints load and render the full house style
def test_legacy_checkpoint_renders_full_style():
    style = _legacy_style()
    assert not style.is_rich()
    block = render_style_block(style, _legacy_characters())
    assert style.style_description in block
    for example in style.examples + HOUSE_EXAMPLES:
        assert example in block
    assert HOUSE_NARRATIVE_DISTANCE.splitlines()[0] in block
    assert "Elena Marchetti, Marcus Reid, Vivian Shaw, Camille Baptiste, Priya Desai: no voice sheet yet" in block
    assert "Revision checklist" in block


# ##################################################################
# rich style fields replace house defaults and voices are listed
def test_rich_style_renders_book_choices():
    style = _legacy_style().model_copy(
        update={
            "narrative_distance": "Tight on Elena; never inside Marcus.",
            "character_voices": [CharacterVoice(name="Elena Marchetti", diction="load paths, punch lists")],
            "rhythm": "Long sentences for walking a building.",
            "positive_examples": ["Elena counted the joists twice."],
            "revision_brief": "Cut any jazz metaphor Elena would not know.",
        }
    )
    assert style.is_rich()
    block = render_style_block(style, _legacy_characters())
    assert "Tight on Elena; never inside Marcus." in block
    assert HOUSE_NARRATIVE_DISTANCE.splitlines()[0] not in block
    assert "- Elena Marchetti: load paths, punch lists" in block
    assert "Marcus Reid, Vivian Shaw, Camille Baptiste, Priya Desai: no voice sheet yet" in block
    assert "Elena counted the joists twice." in block
    assert "Cut any jazz metaphor Elena would not know." in block


# ##################################################################
# merge keeps every existing decision
def test_merge_styles_never_overwrites():
    legacy = _legacy_style()
    filled = WritingStyle(style_description="other", tone="other", voice="other", pacing="other", rhythm="new")
    merged = merge_styles(legacy, filled)
    assert merged.style_description == legacy.style_description
    assert merged.examples == legacy.examples
    assert merged.rhythm == "new"


# ##################################################################
# metadata keeps the author's directive and old metadata still loads
def test_metadata_style_directive_round_trip():
    old = {
        "title": "T", "description": "D", "status": "ongoing", "created_at": "a", "updated_at": "b",
        "author": "A", "num_chapters": 1, "sections_per_chapter": 1,
    }
    assert BookMetadata(**old).style_directive is None
    meta = BookMetadata(**old, style_directive="Spare, wry, close third.")
    assert BookMetadata(**json.loads(meta.model_dump_json())).style_directive == "Spare, wry, close third."


# ##################################################################
# old section checkpoints load with an empty review
def test_section_result_review_defaults():
    assert SectionResult(text="x").review == {}


# ##################################################################
# every scene prompt carries the full style; the system prompt names no
# characters from another book
def test_scene_prompt_carries_style_block():
    from models import Chapter, Section

    chapter = Chapter(
        number=2, title="Storm", opening_situation="o", chapter_goal="g", closing_situation="c", key_events=["k"]
    )
    section = Section(number=1, goal="fix the generator", key_events="it starts")
    block = render_style_block(_legacy_style(), _legacy_characters())
    prompt = _build_scene_prompt(chapter, section, "Continue.", "", False, _legacy_characters(), block)
    assert block in prompt
    assert "Marcus" not in _SYSTEM_TEMPLATE and "Elena" not in _SYSTEM_TEMPLATE
    speakers = _example_speakers(_legacy_characters())
    assert speakers == {"speaker_a": "Elena Marchetti", "speaker_b": "Marcus Reid"}
    assert _example_speakers([])["speaker_a"] == "Speaker One"
    assert "PATTERN BUDGET" in PROSE_CRAFT


# ##################################################################
# leading narration survives cleaning (regression: it used to be dropped)
def test_clean_narrative_keeps_leading_narration():
    raw = "Here is the scene:\n\nNARRATOR: The rain had not stopped.\nElena: \"Coming?\"\nNARRATOR: He looked up."
    lines = _parse_tagged(_clean_narrative(raw))
    assert lines[0] == {"speaker": "NARRATOR", "text": "The rain had not stopped."}
    assert _prose_from_lines(lines).startswith("The rain had not stopped.")


# ##################################################################
# clean scenes skip revision without calling the model
def test_review_scene_skips_clean_scene():
    scene = _scene_from_tagged('NARRATOR: Nell coiled the stern line.\nTomas: "Engine\'s missing."')
    chosen, review = review_scene("conv-unused", scene, _legacy_style())
    assert chosen is scene
    assert review["revised"] is False
    assert "revision" not in review


# ##################################################################
# revision prompt quotes the scene and the book checklist
def test_revision_prompt_contents():
    scene = TaggedScene([], (SAMPLES / "generated/model_1.txt").read_text(encoding="utf-8"))
    style = _legacy_style().model_copy(update={"revision_brief": "No jazz metaphors for Elena."})
    prompt = build_revision_prompt(scene.report, style)
    assert scene.report.tripped()[0].examples[0] in prompt
    assert "No jazz metaphors for Elena." in prompt
    assert "A device's presence alone is not a defect" in prompt


# a deliberately repetitive draft: it leans on contrast framing, stock phrases
# and staccato triads far past the review triggers
_REPETITIVE_DRAFT = """NARRATOR: The generator coughed. Elena froze. The lights died.
NARRATOR: It wasn't fear. It was something older. The silence stretched between them, and the weight of the storm hung in the air.
Marcus: "It's not the grid, but the panel."
NARRATOR: She let out a breath. Not because she was relieved, but because she was tired. A flicker of doubt crossed her face.
Elena: "I hear you. That's valid. You don't have to carry this alone."
NARRATOR: Something shifted. It wasn't hope. It was arithmetic. The silence stretched again, and the weight of the hours pressed on her.
Marcus: "It's not the wiring, but the fuel."
NARRATOR: She checked the gauge. She checked the hose. She checked the clock. The weight of the night hung in the air.
Elena: "It wasn't the fuel. It was the valve."
NARRATOR: Not because she knew, but because she had to. A flicker of something crossed his face. Something shifted between them."""


# ##################################################################
# real revision through the agentd3 daemon
# the subagent first restates the draft as its own output (so "the scene you
# just wrote" is true), then review_scene asks for a revision. the revised
# scene must keep the tagged format and lower the counted excess.
def test_review_scene_revises_with_real_subagent():
    _require_daemon()
    system = _SYSTEM_TEMPLATE.format(
        all_chapters_summary="Chapter 1: Storm - keep the hotel running (ends: power restored)",
        character_block="- Elena Marchetti (protagonist): architect\n- Marcus Reid (supporting): pianist",
        engine_block="",
        craft=PROSE_CRAFT,
        speaker_a="Elena Marchetti",
        speaker_b="Marcus Reid",
    )
    conv = create_subagent(system_prompt=system, title="noveliser2 test review_scene")
    echoed = run_to_completion(conv, "Output exactly these tagged lines, verbatim, nothing else:\n" + _REPETITIVE_DRAFT)
    draft = _scene_from_tagged(echoed)
    assert draft.report.needs_revision
    chosen, review = review_scene(conv, draft, _legacy_style())
    assert "revision" in review
    assert review["revised"] is True
    assert chosen.lines and chosen.report.excess() < draft.report.excess()
    speakers = {line["speaker"] for line in chosen.lines}
    assert speakers <= {"NARRATOR", "Elena", "Elena Marchetti", "Marcus", "Marcus Reid"}


# ##################################################################
# real enrichment of an old checkpoint through the planning model
def test_enrich_legacy_style_with_real_model():
    _require_daemon()
    legacy = _legacy_style()
    outline = (SAMPLES / "legacy_outline.md").read_text(encoding="utf-8")
    characters = _legacy_characters()
    rich = enrich_writing_style(legacy, outline, ["Love and Relationships", "Hope"], characters)
    assert rich.is_rich()
    assert rich.style_description == legacy.style_description
    assert rich.examples == legacy.examples
    voiced = {v.name for v in rich.character_voices}
    assert {"Elena Marchetti", "Marcus Reid"} <= voiced
    assert enrich_writing_style(rich, outline, [], characters) is rich


# ##################################################################
# free-text voices from a model are kept, not rejected
def test_string_voices_are_coerced():
    style = WritingStyle(
        style_description="s", tone="t", voice="v", pacing="p",
        character_voices=[
            "ELENA MARCHETTI (Chicago, architect): load paths and punch lists.",
            "Marcus Reid: musical, oblique.",
            "no recognisable name here",
            {"name": "Priya Desai", "diction": "deal terms"},
        ],
    )
    names = [v.name for v in style.character_voices]
    assert names == ["Elena Marchetti", "Marcus Reid", "", "Priya Desai"]
    assert "load paths" in style.character_voices[0].diction
    assert style.character_voices[2].diction == "no recognisable name here"


# ##################################################################
# scene prompt fixtures
def _chapter_and_section():
    from models import Chapter, Section

    chapter = Chapter(
        number=2, title="Storm", opening_situation="o", chapter_goal="g", closing_situation="c", key_events=["k"]
    )
    return chapter, Section(number=1, goal="fix the generator", key_events="it starts")


# ##################################################################
# later scenes restate the accepted ending as canon; the first scene does not
def test_scene_prompt_restates_accepted_canon():
    chapter, section = _chapter_and_section()
    accepted = "The lamp went out.\n\nElena found the torch by touch."
    later = _build_scene_prompt(chapter, section, "Continue.", "", False, [], "STYLE", accepted)
    assert "ACCEPTED STORY SO FAR" in later
    assert later.index("ACCEPTED STORY SO FAR") < later.index("STYLE")
    assert "Elena found the torch by touch.\n>>>" in later
    first = _build_scene_prompt(chapter, section, "Begin.", "", True, [], "STYLE", accepted)
    assert "ACCEPTED STORY SO FAR" not in first


# ##################################################################
# accepted tail keeps the end of the story and cuts on a paragraph
def test_accepted_tail():
    assert accepted_tail("") == ""
    assert accepted_tail("short text") == "short text"
    story = "\n\n".join(f"Paragraph {i} " + "word " * 40 for i in range(200))
    tail = accepted_tail(story, limit=2000)
    assert story.strip().endswith(tail)
    assert tail.startswith("Paragraph ")
    assert len(tail) <= 2000


# ##################################################################
# reuse decision: a rejected revision poisons the thread, so drop it
def test_next_subagent_id():
    assert next_subagent_id("conv-a", {"draft": "x", "revised": False}) == "conv-a"
    assert next_subagent_id("conv-a", {"draft": "x", "revision": "y", "revised": True}) == "conv-a"
    assert next_subagent_id("conv-a", {"draft": "x", "revision": "y", "revised": False}) is None


# ##################################################################
# a revision may not introduce a speaker the draft did not have
def test_revision_rejects_new_speakers():
    draft = _scene_from_tagged(_REPETITIVE_DRAFT)
    clean = (
        "NARRATOR: The generator coughed and the lights went out over the bar.\n"
        'Marcus: "Panel."\nNARRATOR: Elena held the torch on the fuse box while he worked the screws loose.\n'
        'Elena: "Fuel\'s fine."\nNARRATOR: She read the gauge twice anyway, then the clock above the till.'
    )
    padded = clean + "\nNARRATOR: " + " ".join(["She counted the spare cans by the door again."] * 14)
    good = _scene_from_tagged(padded)
    assert good.report.excess() < draft.report.excess()
    assert _revision_is_better(draft, good)
    intruder = _scene_from_tagged(padded + '\nGerald: "Grid\'s down."')
    assert not _revision_is_better(draft, intruder)
    full_names = _scene_from_tagged(padded.replace("Marcus:", "Marcus Reid:").replace("Elena:", "Elena Marchetti:"))
    assert _revision_is_better(draft, full_names)
