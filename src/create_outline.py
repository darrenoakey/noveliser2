from brain import chat
from craft import STRUCTURE_INSTRUCTION
from models import Character


# ##################################################################
# create outline
# build a detailed story outline that fits the specified scope
def create_outline(description: str, plot_type: str, themes: list[str],
                   characters: list[Character], num_chapters: int,
                   sections_per_chapter: int) -> str:
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
- one short paragraph on how the key supporting characters pressure that arc

Keep the whole response under 1200 words. The story should feel complete and satisfying at this length, not like a fragment or the beginning of a longer work."""},
    ]
    return chat(messages, max_tokens=1536)
