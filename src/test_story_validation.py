import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from models import (  # noqa: E402
    Chapter, ChapterPlan, Character, CharactersList, Relationship, Section, SectionPlan,
    GeneratedCharactersList, GeneratedChapterPlan, GeneratedSectionPlan,
)
from story_validation import (  # noqa: E402
    StoryPlanError, collect_setups, plan_with_feedback, validate_chapter_plan, validate_characters,
    validate_prose, validate_section_plan, with_feedback,
)


def cast() -> CharactersList:
    return CharactersList(characters=[
        Character(name="Mara", biography="b", role="protagonist", traits=["wry"], wound="w", lie="l", want="w", need="n",
                  arc="positive change", flaw="interrupts", voice="clipped, jokes", arc_pressure="betrayal",
                  relationships=[Relationship(other="Venn", dynamic="rival mentor")]),
        Character(name="Venn", biography="b", role="antagonist", traits=[], wound="w", lie="l", want="w", need="n",
                  arc="corruption", flaw="hoards", voice="formal", arc_pressure="loss",
                  relationships=[Relationship(other="Mara", dynamic="former student")]),
        Character(name="Oz", biography="b", role="supporting", traits=[], want="money", voice="drawl"),
    ])


def chapter(n: int, **kw) -> Chapter:
    base = dict(number=n, title=f"T{n}", opening_situation="o", chapter_goal="g", closing_situation="c", key_events=["e", "The silver key is touched"],
                pov_character="Mara", cause_from_previous="because of ch before", pursuit="p", opposition="o",
                stakes="s", choice="ch", cost="co", reversal="r", value_before=f"v{n}", value_after=f"v{n + 1}",
                open_question="q?")
    base.update(kw)
    return Chapter(**base)


def good_plan() -> ChapterPlan:
    return ChapterPlan(
        chapters=[chapter(1, cause_from_previous="", setups=["silver-key"], subplot="Oz debt", subplot_change="owes"),
                  chapter(2, payoffs=["Silver-Key"], subplot="Oz debt", subplot_change="pays"),
                  chapter(3, open_question="")],
        central_question="who stole it?", subplots=["Oz debt"])


def section(n: int, **kw) -> Section:
    base = dict(number=n, goal="g", key_events="k", scene_type="scene", disaster="d", pov_character="Mara", cause="c",
                obstacle="ob", choice="ch", cost="co", value_before="a", value_after="b", next_obligation="next")
    base.update(kw)
    return Section(**base)


def test_valid_cast_and_plan_pass():
    assert validate_characters(cast()) == []
    assert validate_chapter_plan(good_plan(), cast().characters, 3) == []


def test_cast_deficiencies_are_specific():
    c = cast()
    c.characters[0].flaw = ""
    c.characters[1].relationships = [Relationship(other="Ghost", dynamic="x")]
    issues = validate_characters(c)
    assert any("'Mara'" in i and "flaw" in i for i in issues)
    assert any("Ghost" in i for i in issues)
    c.characters[1].relationships = []
    issues = validate_characters(c)
    assert any("Venn" in i and "at least one relationship" in i for i in issues)


def test_chapter_plan_catches_causal_holes():
    plan = good_plan()
    plan.chapters[1].cause_from_previous = ""
    plan.chapters[1].payoffs = ["missing-clue"]
    plan.chapters[2].value_after = plan.chapters[2].value_before
    plan.chapters[2].pov_character = "Nobody"
    plan.chapters[0].open_question = ""
    issues = validate_chapter_plan(plan, cast().characters, 3)
    joined = "\n".join(issues)
    assert "chapter 2: missing cause_from_previous" in joined
    assert "payoff 'missing-clue' has no earlier setup" in joined
    assert "chapter 3: value_after is identical" in joined
    assert "'Nobody' is not a character" in joined
    assert "chapter 1: missing open_question" in joined


def test_unpaid_setup_and_unadvanced_subplot_and_count():
    plan = good_plan()
    plan.chapters[1].payoffs = []
    plan.subplots.append("Venn secret")
    issues = validate_chapter_plan(plan, cast().characters, 4)
    joined = "\n".join(issues)
    assert "setup 'silverkey' is never paid off" in joined.replace("-", "")
    assert "subplot 'Venn secret' is never advanced" in joined
    assert "expected exactly 4 chapters, got 3" in joined


def test_payoff_is_single_not_repeated_for_every_mention():
    plan = good_plan()
    plan.chapters[2].payoffs = ["silver-key"]
    assert any("repeats chapter 2" in issue for issue in validate_chapter_plan(plan, cast().characters, 3))


def test_setup_must_be_visible_in_events_and_planted_only_once():
    plan = good_plan()
    plan.chapters[0].key_events = ["No object appears here"]
    plan.chapters[1].setups = ["silver-key"]
    issues = validate_chapter_plan(plan, cast().characters, 3)
    assert any("absent from key_events" in issue for issue in issues)
    assert any("was already planted" in issue for issue in issues)


def test_setup_identifier_can_have_a_human_explanation():
    plan = good_plan()
    plan.chapters[0].setups = ["silver-key: planted in a cabinet before anyone suspects its purpose"]
    plan.chapters[1].payoffs = ["silver-key: opens the lock after the character loses access"]
    assert validate_chapter_plan(plan, cast().characters, 3) == []


def test_unplanted_multi_chapter_plan_is_rejected():
    plan = good_plan()
    plan.chapters[0].setups = []
    plan.chapters[1].payoffs = []
    assert any("plant at least one" in issue for issue in validate_chapter_plan(plan, cast().characters, 3))


def test_payoff_before_plant_is_rejected():
    plan = good_plan()
    plan.chapters[0].payoffs = ["silver-key"]
    assert any("chapter 1: payoff" in i for i in validate_chapter_plan(plan, cast().characters, 3))


def test_section_plan_valid_and_invalid():
    ch = chapter(2)
    ok = SectionPlan(sections=[section(1, cause="", setups=["lamp"]), section(2, payoffs=["lamp", "silver-key"], next_obligation="")])
    assert validate_section_plan(ok, ch, cast().characters, 2, prior_setups=["silver-key"]) == []
    bad = SectionPlan(sections=[section(1), section(2, cause="", scene_type="montage", value_after="a", payoffs=["nope"])])
    joined = "\n".join(validate_section_plan(bad, ch, cast().characters, 3))
    assert "expected exactly 3 sections" in joined
    assert "section 2: missing cause" in joined
    assert "scene_type must be" in joined
    assert "identical to value_before" in joined
    assert "payoff 'nope'" in joined


def test_collect_setups_only_earlier_chapters():
    plan = good_plan()
    assert collect_setups(plan.chapters, 2) == ["silver-key"]
    assert collect_setups(plan.chapters, 1) == []


def test_prose_validation():
    good = "She walked the quay. " * 200
    assert validate_prose(good) == []
    assert any("words" in i for i in validate_prose("Too short."))
    assert any("meta-text" in i for i in validate_prose("Here is the section:\n" + good))
    assert any("meta-text" in i for i in validate_prose("## Chapter 1\n" + good))
    # intentional repetition is not flagged
    assert validate_prose("Again. " * 700) == []


def test_replanning_feeds_specific_issues_and_is_bounded():
    seen: list[list[str]] = []

    def build(issues: list[str]) -> ChapterPlan:
        seen.append(list(issues))
        plan = good_plan()
        if len(seen) < 3:
            plan.chapters[1].cause_from_previous = ""
        return plan

    result = plan_with_feedback(build, lambda p: validate_chapter_plan(p, cast().characters, 3), "chapter plan")
    assert seen[0] == [] and "missing cause_from_previous" in seen[1][0] and seen[2] == seen[1]
    assert result.chapters[1].cause_from_previous

    calls = []

    def always_bad(issues):
        calls.append(1)
        plan = good_plan()
        plan.chapters[1].cause_from_previous = ""
        return plan

    with pytest.raises(StoryPlanError) as e:
        plan_with_feedback(always_bad, lambda p: validate_chapter_plan(p, cast().characters, 3), "chapter plan", max_attempts=2)
    assert len(calls) == 2 and e.value.attempts == 2 and e.value.issues


def test_generation_value_errors_are_retried_with_feedback():
    seen = []

    def build(issues):
        seen.append(issues)
        if len(seen) == 1:
            raise ValueError("Requested 3 chapters, got 2")
        return good_plan()

    plan_with_feedback(build, lambda p: [], "chapter plan")
    assert seen[1] == ["generation error: Requested 3 chapters, got 2"]


def test_with_feedback_appends_message_without_mutating():
    base = [{"role": "user", "content": "x"}]
    assert with_feedback(base, []) is base
    out = with_feedback(base, ["a is missing"])
    assert len(base) == 1 and "a is missing" in out[-1]["content"]
    revised = with_feedback(base, ["payoff has no setup"], '{"setups":["red-thread"]}')
    assert [item["role"] for item in revised] == ["user", "assistant", "user"]
    assert "red-thread" in revised[1]["content"]


def test_generation_schema_demands_causal_fields_without_breaking_old_checkpoints():
    for schema, item, field in (
        (GeneratedCharactersList, "characters", "lie"),
        (GeneratedChapterPlan, "chapters", "choice"),
        (GeneratedSectionPlan, "sections", "obstacle"),
    ):
        defs = schema.model_json_schema()["$defs"]
        item_type = schema.model_fields[item].annotation.__args__[0].__name__
        assert field in defs[item_type]["required"]


def test_legacy_checkpoints_still_load():
    legacy_chapters = {"chapters": [{"number": 1, "title": "t", "opening_situation": "o", "chapter_goal": "g",
                                     "closing_situation": "c", "key_events": ["e"]}]}
    legacy_sections = {"sections": [{"number": 1, "goal": "g", "key_events": "k"}]}
    legacy_cast = {"characters": [{"name": "A", "biography": "b", "role": "minor", "traits": []}]}
    assert ChapterPlan(**json.loads(json.dumps(legacy_chapters))).chapters[0].setups == []
    assert SectionPlan(**legacy_sections).sections[0].scene_type == "scene"
    assert CharactersList(**legacy_cast).characters[0].relationships == []
    # round trip of the new schema through the raw checkpoint format
    plan = good_plan()
    assert ChapterPlan(**json.loads(json.dumps(plan.model_dump()))) == plan


def test_unique_miracle_rejects_a_predecessor_and_allows_the_protagonist():
    from story_validation import PremiseGuard, validate_premise, validate_unique_miracle

    stolen = (
        "Nessa warns that Silas once had a partner who performed real magic and died making a bird fly."
    )
    assert validate_unique_miracle(stolen, "Tomas")
    allowed = (
        "Tomas performed real magic when the coin sank through oak. "
        "Silas finally admits the boy's magic was real, and nobody else can do it."
    )
    assert validate_unique_miracle(allowed, "Tomas") == []
    named = "Silas performed real magic behind the wagon."
    assert any("Silas" in issue for issue in validate_unique_miracle(named, "Tomas"))
    assert validate_unique_miracle("Though Tomas performed real magic.", "Tomas") == []

    guard = PremiseGuard(
        protagonist="Tomas",
        required_phrases=("floodgate", "engineer"),
        forbidden=((r"\bpyre\b", "do not use a pyre crisis"),),
    )
    clean = (
        "Tomas performed real magic at the failing floodgate after the engineer hid an unsafe repair."
    )
    assert validate_premise(clean, guard) == []
    assert any("floodgate" in issue for issue in validate_premise("Tomas performed real magic.", guard))
    assert any("pyre" in issue for issue in validate_premise(clean + " Corvin builds a pyre.", guard))
    assert any("partner who performed" in issue for issue in validate_premise(clean + " " + stolen, guard))
    named_engineer = PremiseGuard(protagonist="Tomas", allowed_names=("Tomas", "Silas"))
    assert any("Engineer Kaelen" in issue for issue in validate_premise("Engineer Kaelen hides the repair.", named_engineer))
    assert validate_premise("the engineer hides the repair.", named_engineer) == []
