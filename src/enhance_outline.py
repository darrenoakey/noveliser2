from brain import chat, OPUS_MODEL
from models import EnhancedOutline


# ##################################################################
# enhance outline
# enrich the story outline with humor and romance elements
def enhance_outline(outline: str) -> EnhancedOutline:
    messages = [
        {"role": "system", "content": "You are a story editor specializing in adding depth through humor and romance."},
        {"role": "user", "content": f"""Review this outline and enhance it with subtle humor and romance:

{outline}

Add:
1. At least one humorous subplot or character quirk
2. A romantic element (doesn't have to be the main focus)
3. Moments of levity to balance any serious themes

Return the enhanced outline while preserving the core story.

At the end, list:
HUMOR ELEMENTS:
- (each humor element on its own line)

ROMANCE ELEMENTS:
- (each romance element on its own line)"""},
    ]
    result_text = chat(messages, model=OPUS_MODEL)

    outline_text = result_text
    humor_elements = []
    romance_elements = []

    if "HUMOR ELEMENTS:" in result_text:
        parts = result_text.split("HUMOR ELEMENTS:")
        outline_text = parts[0].strip()
        remainder = parts[1]
        if "ROMANCE ELEMENTS:" in remainder:
            humor_part, romance_part = remainder.split("ROMANCE ELEMENTS:")
            humor_elements = [line.strip("- ").strip() for line in humor_part.strip().split("\n") if line.strip() and line.strip() != "-"]
            romance_elements = [line.strip("- ").strip() for line in romance_part.strip().split("\n") if line.strip() and line.strip() != "-"]
        else:
            humor_elements = [line.strip("- ").strip() for line in remainder.strip().split("\n") if line.strip() and line.strip() != "-"]

    return EnhancedOutline(
        outline=outline_text if outline_text else result_text,
        humor_elements=humor_elements[:5],
        romance_elements=romance_elements[:5],
    )
