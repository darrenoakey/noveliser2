"""Real tests for plot planning + character arcs. Pure logic where possible;
live-backend tests skip cleanly when the model box is unreachable (no mocks)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from character_arcs import create_character_arcs  # noqa: E402
from create_plots import (  # noqa: E402
    normalize_plots,
    plan_plots,
    subplot_count,
)
from models import (  # noqa: E402
    Character,
    CharacterArc,
    CharacterArcs,
    CharacterRole,
    Plot,
    PlotSet,
)


def _backend_available() -> bool:
    try:
        from brain import chat

        out = chat([{"role": "user", "content": "Reply with the single word: ok"}], max_tokens=16)
        return bool(out)
    except Exception:
        return False


BACKEND_OK = _backend_available()
skip_if_no_backend = pytest.mark.skipif(not BACKEND_OK, reason="model backend unreachable")


# ##################################################################
# subplot_count boundaries
def test_subplot_count_boundaries():
    assert subplot_count(1) == 1
    assert subplot_count(2) == 1
    assert subplot_count(3) == 1
    assert subplot_count(6) == 2
    assert subplot_count(9) == 3
    assert subplot_count(10) == 3
    assert subplot_count(12) == 4
    assert subplot_count(30) == 4


# ##################################################################
# model construction with defaults
def test_plot_defaults():
    p = Plot(name="x")
    assert p.kind == "subplot"
    assert p.premise == ""
    assert p.stakes == ""
    assert p.characters_involved == []
    assert p.resolution == ""
    assert p.story == ""


def test_plot_old_shape_dict_loads_with_defaults():
    # backward compat: a checkpoint written before the extra fields existed
    p = Plot(**{"name": "just a name"})
    assert p.name == "just a name"
    assert p.kind == "subplot"
    assert p.characters_involved == []


def test_plotset_default_empty():
    ps = PlotSet()
    assert ps.plots == []


def test_plot_roundtrip():
    p = Plot(
        name="The Heist",
        kind="primary",
        premise="A thief wants the crown.",
        stakes="Her sister's freedom.",
        characters_involved=["Mara", "Ivo"],
        resolution="She trades the crown for the sister.",
        story="Once upon a time...",
    )
    dumped = p.model_dump()
    again = Plot(**dumped)
    assert again == p


def test_plotset_roundtrip():
    ps = PlotSet(plots=[Plot(name="A", kind="primary"), Plot(name="B")])
    again = PlotSet(**ps.model_dump())
    assert again == ps
    assert [p.name for p in again.plots] == ["A", "B"]


def test_character_arc_defaults():
    a = CharacterArc(character="Mara")
    assert a.before == ""
    assert a.after == ""
    assert a.change_kind == "growth"
    assert a.journey == ""


def test_character_arc_old_shape_dict_loads():
    a = CharacterArc(**{"character": "Ivo"})
    assert a.character == "Ivo"
    assert a.change_kind == "growth"


def test_character_arcs_roundtrip():
    arcs = CharacterArcs(arcs=[CharacterArc(character="Mara", change_kind="terminal")])
    again = CharacterArcs(**arcs.model_dump())
    assert again == arcs
    assert again.arcs[0].change_kind == "terminal"


# ##################################################################
# normalize_plots pure logic
def test_normalize_promotes_first_when_no_primary():
    plots = [Plot(name="A"), Plot(name="B")]
    out = normalize_plots(plots)
    assert out[0].name == "A"
    assert out[0].kind == "primary"
    assert out[1].kind == "subplot"


def test_normalize_moves_primary_to_front_preserving_subplot_order():
    plots = [
        Plot(name="Sub1"),
        Plot(name="Main", kind="primary"),
        Plot(name="Sub2"),
    ]
    out = normalize_plots(plots)
    assert [p.name for p in out] == ["Main", "Sub1", "Sub2"]
    assert out[0].kind == "primary"
    assert all(p.kind == "subplot" for p in out[1:])


def test_normalize_demotes_extra_primaries():
    plots = [
        Plot(name="First", kind="primary"),
        Plot(name="Second", kind="primary"),
        Plot(name="Third"),
    ]
    out = normalize_plots(plots)
    assert out[0].name == "First"
    assert out[0].kind == "primary"
    assert out[1].kind == "subplot"
    assert out[2].kind == "subplot"
    # exactly one primary survives
    assert sum(1 for p in out if p.kind == "primary") == 1


def test_normalize_empty():
    assert normalize_plots([]) == []


# ##################################################################
# live-backend tests (skip cleanly when unreachable)
def _sample_characters() -> list[Character]:
    return [
        Character(
            name="Mara",
            biography="A dockside thief who lost her parents to the guild's debt collectors.",
            role=CharacterRole.PROTAGONIST,
            traits=["cunning", "loyal"],
        ),
        Character(
            name="Ivo",
            biography="The guild's youngest enforcer, secretly sick of the killing.",
            role=CharacterRole.ANTAGONIST,
            traits=["cold", "conflicted"],
        ),
    ]


@skip_if_no_backend
def test_plan_plots_live():
    ps = plan_plots(
        description="A thief and an enforcer collide over a stolen ledger.",
        plot_type="Overcoming the Monster",
        themes=["Justice", "Betrayal"],
        characters=_sample_characters(),
        num_chapters=3,
    )
    assert ps.plots
    assert ps.plots[0].kind == "primary"
    assert sum(1 for p in ps.plots if p.kind == "primary") == 1
    # 1 primary + subplot_count(3)==1 subplot expected, but be tolerant of the model
    assert len(ps.plots) >= 2


@skip_if_no_backend
def test_create_character_arcs_live():
    chars = _sample_characters()
    plots = PlotSet(
        plots=[
            Plot(
                name="The Ledger",
                kind="primary",
                premise="Mara steals the guild ledger that names her parents' killers.",
                stakes="Her own life and the truth about her family.",
                characters_involved=["Mara", "Ivo"],
                resolution="Mara exposes the guild; Ivo lets her go.",
                story="Mara slipped through the counting-house window...",
            )
        ]
    )
    arcs = create_character_arcs(chars, plots)
    names = {a.character.strip().lower() for a in arcs.arcs}
    # full coverage guaranteed by the backfill
    assert "mara" in names
    assert "ivo" in names


# ##################################################################
# competition-grade standalone story (live; slow — one full PROSE_TIER story)
def test_write_plot_story_is_competition_length_standalone_live():
    if not BACKEND_OK:
        pytest.skip("model backend unreachable")
    from create_plots import STORY_WORD_LO, write_plot_story
    from models import CharacterRole

    cast = [
        Character(name="Nell Harker", biography="A tide-pool ecologist who charts the reef alone since her brother drowned.", role=CharacterRole.PROTAGONIST, traits=["stubborn", "observant"]),
        Character(name="Joan Mercer", biography="The harbourmaster who signs the storm warnings nobody reads.", role=CharacterRole.SUPPORTING, traits=["dry", "dutiful"]),
    ]
    plot = Plot(
        name="The Ninth Wave",
        kind="primary",
        premise="Nell finds her brother's lost dive slate wedged in the reef the day a king tide is due, and has one falling tide to reach it.",
        stakes="The slate — his last message — will be ground to powder by the king tide.",
        characters_involved=["Nell Harker", "Joan Mercer"],
        resolution="Nell reaches the slate, reads his final joke, and lets the sea keep the slate but not the words.",
    )
    story = write_plot_story(plot, [], cast, "A windswept coastal town where the sea gives and takes.")
    words = len(story.split())
    assert words >= int(STORY_WORD_LO * 0.5), f"story too short to be a real short story: {words} words"
    assert story.strip()[-1] in ".!?\"”’)—…", "story must end cleanly"
    head = story[:800].lower()
    assert "analyze user input" not in head and "pov/tense" not in head
