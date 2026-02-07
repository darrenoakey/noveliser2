from brain import chat_structured, OPUS_MODEL
from models import ChapterPlan, Character, EnhancedOutline


# ##################################################################
# break into chapters
# divide the enhanced outline into detailed chapter plans
def break_into_chapters(enhanced_outline: EnhancedOutline, characters: list[Character],
                        themes: list[str], plot_type: str, num_chapters: int) -> ChapterPlan:
    character_list = "\n".join([f"- {c.name} ({c.role.value}): {c.biography}" for c in characters])
    theme_list = ", ".join(themes)
    humor_text = "\n".join(f"- {h}" for h in enhanced_outline.humor_elements) if enhanced_outline.humor_elements else "None specified"
    romance_text = "\n".join(f"- {r}" for r in enhanced_outline.romance_elements) if enhanced_outline.romance_elements else "None specified"

    messages = [
        {"role": "system", "content": "You are a story development expert who takes story outlines and creates detailed chapter breakdowns that progress the overall story."},
        {"role": "user", "content": f"""Here's a story outline with all elements. Flesh this out into EXACTLY {num_chapters} chapters:

STORY OUTLINE:
{enhanced_outline.outline}

PLOT TYPE: {plot_type}

THEMES: {theme_list}

CHARACTERS:
{character_list}

HUMOR ELEMENTS:
{humor_text}

ROMANCE ELEMENTS:
{romance_text}

For each chapter, provide:
1. TITLE: A compelling chapter title
2. OPENING SITUATION: Where we are at the start (character states, plot situation, setting)
3. CHAPTER GOAL: What this chapter achieves in progressing the overall story
4. CLOSING SITUATION: Where we are at the end (how things have changed)
5. KEY EVENTS: Major plot points and story beats

CRITICAL REQUIREMENTS:
- The chapters must cover the ENTIRE story from beginning to end
- Chapters are parts of the whole story, not independent narrative arcs
- Include the themes, plot type, humor and romance elements throughout
- Ensure proper story pacing and character development across all chapters
- The final chapter must provide complete closure and resolution
- No duplication across chapters

Create exactly {num_chapters} chapters."""},
    ]
    result = chat_structured(messages, ChapterPlan, model=OPUS_MODEL)

    if len(result.chapters) != num_chapters:
        raise ValueError(f"Requested {num_chapters} chapters, got {len(result.chapters)}")

    for i, chapter in enumerate(result.chapters):
        chapter.number = i + 1

    return result
