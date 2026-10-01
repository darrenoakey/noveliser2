"""Generate the small, frozen schedule contract before chapter planning."""

from __future__ import annotations

import json

from pydantic import BaseModel, Field, create_model

from brain import chat_structured
from models import Character, EnhancedOutline, ScheduleContract
from story_validation import (PremiseGuard, plan_with_feedback, validate_premise,
                              validate_schedule_contract, with_feedback)


def bounded_schedule_model(num_chapters: int) -> type[BaseModel]:
    """Schema whose chapter numbers cannot exceed the requested book."""
    last_plant = max(1, num_chapters - 1)
    obligation = create_model(
        f"ObligationFor{num_chapters}",
        id=(str, Field(pattern=r"^[a-z][a-z0-9-]{1,47}$")),
        entity_anchor=(str, Field(min_length=8, max_length=160)),
        plant_chapter=(int, Field(ge=1, le=last_plant)),
        plant_anchor=(str, Field(min_length=8, max_length=240)),
        payoff_chapter=(int, Field(ge=2, le=num_chapters)),
        payoff_anchor=(str, Field(min_length=8, max_length=240)),
    )
    handoff = create_model(
        f"HandoffFor{num_chapters}",
        from_chapter=(int, Field(ge=1, le=last_plant)),
        to_chapter=(int, Field(ge=2, le=num_chapters)),
        consequence_anchor=(str, Field(min_length=8, max_length=240)),
    )
    return create_model(
        f"BoundedScheduleFor{num_chapters}",
        obligations=(list[obligation], Field(min_length=1, max_length=3)),
        handoffs=(list[handoff], Field(min_length=num_chapters - 1, max_length=num_chapters - 1)),
    )


def create_schedule_contract(enhanced_outline: EnhancedOutline, characters: list[Character],
                             num_chapters: int,
                             premise: PremiseGuard | None = None) -> ScheduleContract:
    """Return a bounded, model-authored contract; never infer one in Python."""
    if num_chapters < 2:
        raise ValueError("schedule contracts require at least two chapters")

    outline_json = enhanced_outline.model_dump_json()
    cast_json = json.dumps([character.model_dump() for character in characters])
    base_messages = [
        {
            "role": "system",
            "content": (
                "You define grounded story schedules. Return only JSON matching the "
                "ScheduleContract schema; do not write chapter summaries."
            ),
        },
        {
            "role": "user",
            "content": f"""Define a finite contract for a later chapter planner.

Return one to three obligations and exactly {num_chapters - 1} adjacent handoffs: 1->2, 2->3, and so on through {num_chapters - 1}->{num_chapters}.
There are EXACTLY {num_chapters} chapters. plant_chapter and payoff_chapter must be integers from 1 to {num_chapters}, with payoff strictly later. There is no chapter {num_chapters + 1}. If the outline spills past chapter {num_chapters}, compress the final crisis and resolution into chapter {num_chapters}.

For every obligation:
- choose one concrete entity, promise, clue, object, capability, or relationship state already supported by the outline;
- give it a stable lowercase hyphenated ID;
- set one plant chapter and one strictly later payoff chapter;
- write exact, distinct plant_anchor and payoff_anchor descriptions of the two on-page actions; the later action must use the SAME entity_anchor;
- do not merge similar entities (for example, two different birds or two different sets of ashes).

For every handoff N -> N+1, write the concrete consequence in chapter N that forces chapter N+1.
Do not add people, objects, backstory, events, or causal links absent from or directly incompatible with the supplied outline. Do not add IDs or explanations to anchors. Do not invent a second real magician, a dead predecessor who performed real magic, or a witch-hunt crisis. Do not emit a chapter number above {num_chapters}.

Enhanced outline:
{outline_json}

Selected cast:
{cast_json}
""",
        },
    ]
    schema = bounded_schedule_model(num_chapters)
    prior: ScheduleContract | None = None

    def build(issues: list[str]) -> ScheduleContract:
        nonlocal prior
        draft = prior.model_dump_json() if prior else ""
        generated = chat_structured(with_feedback(base_messages, issues, draft), schema)
        prior = ScheduleContract.model_validate(generated.model_dump())
        return prior

    def validate(schedule: ScheduleContract) -> list[str]:
        issues = validate_schedule_contract(schedule, num_chapters)
        parts = []
        for item in schedule.obligations:
            parts.extend((item.entity_anchor, item.plant_anchor, item.payoff_anchor))
        parts.extend(item.consequence_anchor for item in schedule.handoffs)
        blob = " ".join(parts)
        issues.extend(validate_premise(blob, premise, require_phrases=False))
        return issues

    return plan_with_feedback(build, validate, "schedule contract")
