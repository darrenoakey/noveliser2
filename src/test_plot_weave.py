"""Real tests for the plot-weave craft helpers and the pipeline plot/arc
extract helpers. Pure string/logic — no backend, no mocks.

craft.py has no model dependency for these helpers, so its tests run standalone.
The pipeline extract-helper tests import pipeline (and thus models) lazily inside
the test body so the file stays collectable even before the parallel models.py /
create_plots.py / character_arcs.py additions land.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from craft import (  # noqa: E402
    PLOT_WEAVE_INSTRUCTION,
    render_character_arcs,
    render_plot_stories,
    render_plot_threads,
)


# ##################################################################
# lightweight duck-typed stand-ins so the craft helpers can be exercised without
# importing the (parallel-authored) pydantic models.
class _Plot:
    def __init__(self, name="", kind="subplot", premise="", stakes="",
                 resolution="", story=""):
        self.name = name
        self.kind = kind
        self.premise = premise
        self.stakes = stakes
        self.resolution = resolution
        self.story = story


class _PlotSet:
    def __init__(self, plots):
        self.plots = plots


class _Arc:
    def __init__(self, character="", before="", after="", change_kind="growth",
                 journey=""):
        self.character = character
        self.before = before
        self.after = after
        self.change_kind = change_kind
        self.journey = journey


class _Arcs:
    def __init__(self, arcs):
        self.arcs = arcs


# ##################################################################
# render_plot_threads — empty / None
def test_plot_threads_empty_and_none():
    assert render_plot_threads(None) == ""
    assert render_plot_threads([]) == ""
    assert render_plot_threads(_PlotSet([])) == ""
    assert render_plot_threads({"plots": []}) == ""


# ##################################################################
# render_plot_threads — PlotSet-like, tags + heading + fields
def test_plot_threads_plotset():
    ps = _PlotSet([
        _Plot(name="The Heist", kind="primary", premise="steal the ledger",
              stakes="prison or freedom", resolution="ledger destroyed"),
        _Plot(name="Old Flame", kind="subplot", premise="a rekindled romance",
              stakes="a broken trust", resolution="they part as friends"),
    ])
    out = render_plot_threads(ps)
    assert "PLOT THREADS" in out
    assert "the primary plot is the spine" in out
    assert "[PRIMARY] The Heist" in out
    assert "[SUBPLOT] Old Flame" in out
    assert "steal the ledger" in out
    assert "Stakes: prison or freedom" in out
    assert "Resolves: ledger destroyed" in out


# ##################################################################
# render_plot_threads — plain list of Plot-likes
def test_plot_threads_plain_list():
    out = render_plot_threads([_Plot(name="Solo", kind="primary", premise="p")])
    assert "[PRIMARY] Solo" in out
    assert "— p" in out


# ##################################################################
# render_plot_threads — list of dicts (checkpoint shape)
def test_plot_threads_list_of_dicts():
    out = render_plot_threads([
        {"name": "Spine", "kind": "primary", "premise": "core"},
        {"name": "Side", "kind": "subplot", "premise": "aside",
         "stakes": "small", "resolution": "resolved"},
    ])
    assert "[PRIMARY] Spine" in out
    assert "[SUBPLOT] Side" in out
    assert "Resolves: resolved" in out


# ##################################################################
# render_plot_threads — a plot with no name is skipped
def test_plot_threads_skips_nameless():
    out = render_plot_threads([_Plot(name="", kind="primary"),
                               _Plot(name="Real", kind="subplot")])
    assert "Real" in out
    assert out.count("- [") == 1


# ##################################################################
# render_character_arcs — empty / None
def test_character_arcs_empty_and_none():
    assert render_character_arcs(None) == ""
    assert render_character_arcs([]) == ""
    assert render_character_arcs(_Arcs([])) == ""
    assert render_character_arcs({"arcs": []}) == ""


# ##################################################################
# render_character_arcs — heading, before → after, change_kind incl. terminal
def test_character_arcs_content_and_terminal():
    arcs = _Arcs([
        _Arc(character="Mara", before="trusting", after="hardened",
             change_kind="decline"),
        _Arc(character="Finn", before="alive and hopeful", after="dead",
             change_kind="terminal"),
    ])
    out = render_character_arcs(arcs)
    assert "CHARACTER TRAJECTORIES" in out
    assert "positive, negative, or fatal" in out
    assert "Mara: trusting → hardened [decline]" in out
    assert "Finn: alive and hopeful → dead [terminal]" in out


# ##################################################################
# render_character_arcs — list of dicts (checkpoint shape)
def test_character_arcs_list_of_dicts():
    out = render_character_arcs([
        {"character": "Ivy", "before": "meek", "after": "bold",
         "change_kind": "growth"},
    ])
    assert "Ivy: meek → bold [growth]" in out


# ##################################################################
# render_character_arcs — missing character name is skipped, default change_kind
def test_character_arcs_defaults_and_skip():
    out = render_character_arcs([
        {"character": "", "before": "x", "after": "y"},
        {"character": "Sam", "before": "a", "after": "b"},
    ])
    assert "Sam: a → b [growth]" in out
    assert out.count("- ") == 1


# ##################################################################
# render_plot_stories — with story text present
def test_plot_stories_with_text():
    ps = _PlotSet([
        _Plot(name="Main", kind="primary", story="Once upon a time, a spine."),
        _Plot(name="Aside", kind="subplot", story="Meanwhile, a subplot."),
    ])
    out = render_plot_stories(ps)
    assert "PLOT STORIES" in out
    assert "=== [PRIMARY]: Main ===" in out
    assert "Once upon a time, a spine." in out
    assert "=== [SUBPLOT]: Aside ===" in out
    assert "Meanwhile, a subplot." in out


# ##################################################################
# render_plot_stories — no story text anywhere → ""
def test_plot_stories_without_text():
    ps = _PlotSet([_Plot(name="Main", kind="primary", story="")])
    assert render_plot_stories(ps) == ""
    assert render_plot_stories(None) == ""
    assert render_plot_stories([]) == ""


# ##################################################################
# render_plot_stories — only plots that have a story appear
def test_plot_stories_partial():
    ps = _PlotSet([
        _Plot(name="Told", kind="primary", story="A told tale."),
        _Plot(name="Untold", kind="subplot", story=""),
    ])
    out = render_plot_stories(ps)
    assert "Told" in out
    assert "Untold" not in out


# ##################################################################
# PLOT_WEAVE_INSTRUCTION — key phrases present
def test_plot_weave_instruction_phrases():
    lower = PLOT_WEAVE_INSTRUCTION.lower()
    assert "resolve" in lower
    assert "primary" in lower
    assert "subplot" in lower
    assert "spine" in lower


# ##################################################################
# pipeline._extract_plot_set — pydantic instance passthrough + dict rebuild.
# Imports lazily so this file collects even before the parallel files land.
def test_extract_plot_set_instance_and_dict():
    import pipeline
    from models import Plot, PlotSet

    ps = PlotSet(plots=[Plot(name="A", kind="primary")])
    assert pipeline._extract_plot_set(ps) is ps

    rebuilt = pipeline._extract_plot_set(
        {"plots": [{"name": "A", "kind": "primary", "story": "s"},
                   {"name": "B", "kind": "subplot"}]}
    )
    assert isinstance(rebuilt, PlotSet)
    assert [p.name for p in rebuilt.plots] == ["A", "B"]
    assert rebuilt.plots[0].story == "s"
    # mutation-after-rebuild works (resume story loop relies on this)
    rebuilt.plots[1].story = "later"
    assert rebuilt.plots[1].story == "later"


# ##################################################################
# pipeline._extract_story — dict, model-like, and bare value
def test_extract_story_shapes():
    import pipeline

    assert pipeline._extract_story({"story": "hello"}) == "hello"
    assert pipeline._extract_story({"story": None}) == ""

    class _S:
        story = "obj story"

    assert pipeline._extract_story(_S()) == "obj story"


# ##################################################################
# pipeline._extract_character_arcs — instance passthrough + dict rebuild
def test_extract_character_arcs_instance_and_dict():
    import pipeline
    from models import CharacterArc, CharacterArcs

    arcs = CharacterArcs(arcs=[CharacterArc(character="Q")])
    assert pipeline._extract_character_arcs(arcs) is arcs

    rebuilt = pipeline._extract_character_arcs(
        {"arcs": [{"character": "Q", "before": "b", "after": "a",
                   "change_kind": "terminal"}]}
    )
    assert isinstance(rebuilt, CharacterArcs)
    assert rebuilt.arcs[0].character == "Q"
    assert rebuilt.arcs[0].change_kind == "terminal"
