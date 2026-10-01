import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from models import (  # noqa: E402
    Chapter, ChapterPlan, ScheduleContract, ScheduledHandoff, ScheduledObligation,
)
from story_validation import (  # noqa: E402
    apply_schedule, validate_plan_against_schedule, validate_schedule_contract,
)


def obligation(**changes) -> ScheduledObligation:
    values = {
        "id": "silas-brother-ashes",
        "entity_anchor": "Silas's brother's ashes",
        "plant_chapter": 1,
        "plant_anchor": "Nessa identifies Silas's brother's ashes in the reliquary",
        "payoff_chapter": 3,
        "payoff_anchor": "Tomas resurrects Silas's brother from those ashes",
    }
    values.update(changes)
    return ScheduledObligation(**values)


def schedule(**changes) -> ScheduleContract:
    values = {
        "obligations": [obligation()],
        "handoffs": [
            ScheduledHandoff(from_chapter=1, to_chapter=2,
                             consequence_anchor="Silas forbids Tomas from using real magic"),
            ScheduledHandoff(from_chapter=2, to_chapter=3,
                             consequence_anchor="Corvin publicly accuses Tomas of theft"),
        ],
    }
    values.update(changes)
    return ScheduleContract(**values)


def chapter(number: int, events: list[str], cause: str = "") -> Chapter:
    return Chapter(number=number, title=f"Chapter {number}", opening_situation="opening",
                   chapter_goal="goal", closing_situation="closing", key_events=events,
                   cause_from_previous=cause)


def plan() -> ChapterPlan:
    return ChapterPlan(chapters=[
        chapter(1, ["Nessa identifies Silas's brother's ashes in the reliquary"]),
        chapter(2, ["Corvin confronts Tomas"], "Silas forbids Tomas from using real magic"),
        chapter(3, ["Tomas resurrects Silas's brother from those ashes"],
                "Corvin publicly accuses Tomas of theft"),
    ])


def test_bounded_schedule_schema_caps_chapter_numbers():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from create_schedule_contract import bounded_schedule_model

    schema = bounded_schedule_model(3).model_json_schema()
    defs = schema["$defs"]
    obligation_schema = next(item for item in defs.values() if "payoff_chapter" in item.get("properties", {}))
    assert obligation_schema["properties"]["payoff_chapter"]["maximum"] == 3
    assert obligation_schema["properties"]["plant_chapter"]["maximum"] == 2
    handoff = next(item for item in defs.values() if "to_chapter" in item.get("properties", {}))
    assert handoff["properties"]["to_chapter"]["maximum"] == 3


def test_schedule_integrity_rejects_duplicate_ids_bad_timing_and_handoffs():
    invalid = schedule(
        obligations=[obligation(), obligation()],
        handoffs=[
            ScheduledHandoff(from_chapter=1, to_chapter=2, consequence_anchor="First consequence"),
            ScheduledHandoff(from_chapter=1, to_chapter=2, consequence_anchor="Repeated consequence"),
        ],
    )
    issues = validate_schedule_contract(invalid, 3)
    assert any("duplicate obligation id" in issue for issue in issues)
    assert any("requires exactly one adjacent handoff" in issue for issue in issues)
    assert any("duplicate chapter handoff" in issue for issue in issues)

    bad_timing = schedule(obligations=[obligation(plant_chapter=3, payoff_chapter=3)])
    assert any("strictly increasing" in issue for issue in validate_schedule_contract(bad_timing, 3))
    assert any("no chapter 4" in issue for issue in validate_schedule_contract(bad_timing, 3))


def test_schedule_requires_distinct_event_anchors():
    invalid = schedule(obligations=[obligation(payoff_anchor="Nessa identifies Silas's brother's ashes in the reliquary")])
    assert any("distinct events" in issue for issue in validate_schedule_contract(invalid, 3))


def test_apply_schedule_projects_only_contract_ids():
    candidate = plan()
    candidate.chapters[0].setups = ["invented-clue"]
    candidate.chapters[2].payoffs = ["invented-clue"]
    narrative_before = [
        (list(item.key_events), item.cause_from_previous, item.choice, item.cost)
        for item in candidate.chapters
    ]

    returned = apply_schedule(candidate, schedule())

    assert returned is candidate
    assert [item.setups for item in candidate.chapters] == [["silas-brother-ashes"], [], []]
    assert [item.payoffs for item in candidate.chapters] == [[], [], ["silas-brother-ashes"]]
    assert narrative_before == [
        (list(item.key_events), item.cause_from_previous, item.choice, item.cost)
        for item in candidate.chapters
    ]


def test_plan_validation_rejects_generic_evidence_and_missing_handoff():
    candidate = apply_schedule(plan(), schedule())
    candidate.chapters[0].key_events = ["Nessa studies bird ashes in the reliquary"]
    candidate.chapters[2].cause_from_previous = "Tomas faces the consequences of the accusation"

    issues = validate_plan_against_schedule(candidate, schedule())

    plant = next(issue for issue in issues if "missing scheduled plant evidence" in issue)
    assert "Nessa identifies Silas's brother's ashes in the reliquary" in plant
    handoff = next(issue for issue in issues if "cause_from_previous omits scheduled handoff" in issue)
    assert "Corvin publicly accuses Tomas of theft" in handoff


def test_plan_validation_requires_projected_ids_and_payoff_anchor():
    candidate = plan()
    issues = validate_plan_against_schedule(candidate, schedule())
    assert any("setups do not match" in issue for issue in issues)
    assert any("payoffs do not match" in issue for issue in issues)

    candidate = apply_schedule(plan(), schedule())
    candidate.chapters[2].key_events = ["Tomas leaves the reliquary untouched"]
    issues = validate_plan_against_schedule(candidate, schedule())
    payoff = next(issue for issue in issues if "missing scheduled payoff evidence" in issue)
    assert "Tomas resurrects Silas's brother from those ashes" in payoff
    assert "Paste this sentence unchanged" in payoff
