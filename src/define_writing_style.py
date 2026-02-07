from brain import chat_structured, OPUS_MODEL
from models import WritingStyle


# ##################################################################
# define writing style
# establish a consistent narrative voice and style for the novel
def define_writing_style(outline: str, themes: list[str]) -> WritingStyle:
    messages = [
        {"role": "system", "content": "You are a writing style consultant who defines clear, consistent narrative voices for novels."},
        {"role": "user", "content": f"""Define a consistent writing style for this novel:

Themes: {', '.join(themes)}
Story outline:
{outline}

Provide specific guidance on:
- Overall style description
- Tone (e.g., serious, light, dramatic, humorous)
- Voice (e.g., first-person, third-person limited, omniscient)
- Pacing (e.g., fast-paced, measured, varies by section)
- 2-3 example sentences showing the style"""},
    ]
    return chat_structured(messages, WritingStyle, model=OPUS_MODEL)
