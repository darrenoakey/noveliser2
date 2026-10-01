from brain import chat
from craft import STRUCTURE_INSTRUCTION
from models import Character
from story_validation import (MAX_PLAN_ATTEMPTS, PremiseGuard, StoryPlanError,
                              validate_premise, with_feedback)


# ##################################################################
# create outline
# build a detailed story outline that fits the specified scope
def _premise_block(premise: PremiseGuard | None) -> str:
    if premise is None:
        return ""
    lines = []
    if premise.protagonist:
        lines.append(
            f"Only {premise.protagonist} can perform a real supernatural impossibility. "
            "No partner, relative, mentor, rival, or dead predecessor has ever done real magic."
        )
    if premise.required_phrases:
        lines.append("The outline must visibly include: " + "; ".join(premise.required_phrases) + ".")
    for _pattern, message in premise.forbidden:
        lines.append(message[0].upper() + message[1:] + ".")
    return "\nPREMISE GUARD:\n" + "\n".join(f"- {line}" for line in lines) + "\n"


def create_outline(description: str, plot_type: str, themes: list[str],
                   characters: list[Character], num_chapters: int,
                   sections_per_chapter: int,
                   premise: PremiseGuard | None = None) -> str:
    char_descriptions = "\n".join([f"- {c.name} ({c.role.value}): {c.biography}" for c in characters])
    total_sections = num_chapters * sections_per_chapter

    if num_chapters == 1:
        scope = "This is a complete short story with a full beginning, middle, and end within a single chapter."
    elif num_chapters <= 3:
        scope = f"This is a novella with {num_chapters} chapters that must tell a complete story with full resolution."
    else:
        scope = f"This is a full novel with {num_chapters} chapters with rich development and multiple plot threads."

    messages = [
        {"role": "system", "content": "You are a master story outliner who creates compelling narrative structures that fit perfectly within the specified scope."},
        {"role": "user", "content": f"""Create a detailed story outline that tells a COMPLETE story within exactly {num_chapters} chapters and {total_sections} total sections:

Description: {description}
Plot Type: {plot_type}
Themes: {', '.join(themes)}
Characters:
{char_descriptions}

CAST INVARIANT: These named characters are the whole consequential cast. Do not invent a new named villain, mentor, romantic lead, or hidden wizard in the outline. Anonymous passersby and authorities may exist. If an external crisis needs an agent, use the existing cast's goals and social roles, not a surprise antagonist.

SCOPE: {scope}

{STRUCTURE_INSTRUCTION}

CRITICAL: This outline must contain a complete story arc with:
- Clear beginning that establishes setting, characters, and conflict
- Well-developed middle that explores the conflict and develops characters
- Satisfying resolution that ties up all plot threads
- All major plot points, character development, and thematic elements must fit within {num_chapters} chapters

Return a compact planning outline only:
- 3 acts, mapped to the pacing beats above (inciting incident, plot point one, midpoint, plot point two, climax)
- 2-4 bullet points per act, each connected to the next by "therefore" or "but"
- one short paragraph on the protagonist's emotional journey (their Lie giving way to their Need)
- one short paragraph on how the key supporting characters pressure that arc, using their exact names
- one concrete physical/social threat caused by prior choices and a dated or material constraint; do not substitute vague 'witch-hunt' stakes for a consequential earned crisis

Keep the whole response under 1200 words. The story should feel complete and satisfying at this length, not like a fragment or the beginning of a longer work.
{_premise_block(premise)}"""},
    ]
    prior = ""
    issues: list[str] = []
    for _attempt in range(1, MAX_PLAN_ATTEMPTS + 1):
        text = chat(with_feedback(messages, issues, prior), max_tokens=1536)
        prior = text
        issues = validate_premise(text, premise)
        if not issues:
            return text
    raise StoryPlanError("outline", issues, MAX_PLAN_ATTEMPTS)
