from brain import chat_structured
from craft import HOUSE_EXAMPLES, HOUSE_PATTERN_BUDGET, STYLE_INSTRUCTION
from models import Character, WritingStyle

_SYSTEM = (
    "You are a fiction editor who defines concrete, checkable narrative styles for novels: point-of-view "
    "distance, how each character talks, sentence rhythm, where the images come from, and worked examples."
)

# fields an older checkpoint may lack; enrich_writing_style fills only these
_RICH_FIELDS = ("narrative_distance", "character_voices", "rhythm", "imagery_sources", "positive_examples",
                "revision_brief")


# ##################################################################
# define writing style
# establish a consistent narrative voice and style for the novel, with
# per-character voices when the cast is known
def define_writing_style(
    outline: str,
    themes: list[str],
    style_directive: str | None = None,
    characters: list[Character] | None = None,
) -> WritingStyle:
    prompt = f"""Define the writing style for this novel.

{_context_block(outline, themes, style_directive, characters)}

{STYLE_INSTRUCTION}

Also fill style_description, tone, voice, pacing, and examples (2-3 single sentences in the style).

{_reference_block()}"""
    return chat_structured(_messages(prompt), WritingStyle)


# ##################################################################
# enrich writing style
# upgrade a style from an older checkpoint: keep every existing decision and
# ask only for the concrete craft fields it lacks. a style that already has
# them is returned unchanged, so this is safe to call on every resume.
def enrich_writing_style(
    style: WritingStyle,
    outline: str,
    themes: list[str],
    characters: list[Character] | None = None,
    style_directive: str | None = None,
) -> WritingStyle:
    if style.is_rich():
        return style
    prompt = f"""This novel already has a writing style. Keep it exactly; extend it with the missing concrete fields.

EXISTING STYLE (do not change these decisions):
{style.model_dump_json(indent=2)}

{_context_block(outline, themes, style_directive, characters)}

{STYLE_INSTRUCTION}

Return the full style object: copy the existing fields unchanged and fill {", ".join(_RICH_FIELDS)}.

{_reference_block()}"""
    filled = chat_structured(_messages(prompt), WritingStyle)
    return merge_styles(style, filled)


# ##################################################################
# merge styles
# existing non-empty fields always win; new values only fill blanks
def merge_styles(existing: WritingStyle, filled: WritingStyle) -> WritingStyle:
    merged = existing.model_dump()
    for name, value in filled.model_dump().items():
        if not merged.get(name):
            merged[name] = value
    return WritingStyle(**merged)


# ##################################################################
# context block
# the story facts the style must fit
def _context_block(
    outline: str, themes: list[str], style_directive: str | None, characters: list[Character] | None
) -> str:
    parts = [f"Themes: {', '.join(themes)}", f"Story outline:\n{outline}"]
    if characters:
        parts.append("Cast (give each speaking character a voice entry):\n" + _cast_lines(characters))
    if style_directive:
        parts.append(
            "AUTHOR'S STYLE DIRECTIVE (honor this above all; it defines the desired voice and reading "
            f"experience):\n{style_directive}"
        )
    return "\n\n".join(parts)


# ##################################################################
# cast lines
# one line per character with what decides their diction
def _cast_lines(characters: list[Character]) -> str:
    lines = []
    for c in characters:
        role = c.role.value if hasattr(c.role, "value") else c.role
        lines.append(f"- {c.name} ({role}): {c.biography} Traits: {', '.join(c.traits)}")
    return "\n".join(lines)


# ##################################################################
# reference block
# house register examples and the device budget the style should respect
def _reference_block() -> str:
    examples = "\n".join(f"- {e}" for e in HOUSE_EXAMPLES)
    return (
        "Register reference (passages from other stories; match this level of specificity, never reuse "
        f"their people or events):\n{examples}\n\nThe style must respect this budget:\n{HOUSE_PATTERN_BUDGET}"
    )


# ##################################################################
# messages
# system + user message pair for chat_structured
def _messages(prompt: str) -> list[dict]:
    return [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": prompt}]
