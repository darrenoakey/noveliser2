from brain import chat_structured
from models import EnhancedOutline
from story_validation import (PremiseGuard, plan_with_feedback, validate_premise, with_feedback)


# ##################################################################
# enhance outline
# maintain the plan while enriching only relationships and levity with causal purpose
def enhance_outline(outline: str, premise: PremiseGuard | None = None) -> EnhancedOutline:
    messages = [
        {"role": "system", "content": "You are a developmental editor who writes revised STORY OUTLINES, not critiques or reviews."},
        {"role": "user", "content": f"""Rewrite the story outline below as a story outline, preserving every important plot cause, cost, payoff, time jump and character relationship. Put the NEW STORY OUTLINE itself in the `outline` field: no commentary, praise, review, analysis, editorial notes, headings like 'Review:', or discussion of what you changed. Preserve the complete beginning, middle, and ending.

If an existing relationship, romantic feeling, or levity genuinely changes a consequential decision, sharpen that link and list it in its respective element field. Otherwise leave those lists empty. Do NOT invent romance, a love triangle, jokes, or a new character to fill a beat. Keep all ages and relationships consistent and do not depict an adult-minor romance.

STORY OUTLINE TO REWRITE:
{outline}

Do not give real supernatural magic to anyone except the established protagonist. Do not replace a concrete material crisis with a witch hunt, pyre, or secret wizard."""},
    ]
    prior: EnhancedOutline | None = None

    def build(issues: list[str]) -> EnhancedOutline:
        nonlocal prior
        draft = prior.model_dump_json() if prior else ""
        prior = chat_structured(with_feedback(messages, issues, draft), EnhancedOutline)
        return prior

    return plan_with_feedback(
        build, lambda result: validate_premise(result.outline, premise), "enhanced outline",
    )
