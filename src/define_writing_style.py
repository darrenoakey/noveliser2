from brain import chat_structured
from craft import STYLE_INSTRUCTION
from models import WritingStyle


# ##################################################################
# define writing style
# establish a consistent narrative voice and style for the novel
def define_writing_style(outline: str, themes: list[str], style_directive: str | None = None) -> WritingStyle:
    directive_block = ""
    if style_directive:
        directive_block = (
            f"\nAUTHOR'S STYLE DIRECTIVE (honor this above all — it defines the desired voice "
            f"and reading experience):\n{style_directive}\n"
        )
    messages = [
        {"role": "system", "content": "You are a writing style consultant who defines clear, consistent narrative voices for novels."},
        {"role": "user", "content": f"""Define a consistent writing style for this novel:

Themes: {', '.join(themes)}
Story outline:
{outline}
{directive_block}
{STYLE_INSTRUCTION}

Provide specific guidance on:
- Overall style description
- Tone (e.g., serious, light, dramatic, humorous)
- Voice (e.g., first-person, third-person limited, omniscient)
- Pacing (e.g., fast-paced, measured, varies by section)
- 2-3 example sentences showing the style"""},
    ]
    return chat_structured(messages, WritingStyle)
