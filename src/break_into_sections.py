from brain import chat_structured, OPUS_MODEL
from models import Chapter, SectionPlan


# ##################################################################
# break into sections
# divide a chapter into writing-sized sections with clear goals
def break_into_sections(chapter: Chapter, sections_per_chapter: int, all_chapters: list[Chapter]) -> SectionPlan:
    chapter_context = "\n".join([
        f"  Ch {c.number}: {c.title} - {c.chapter_goal}"
        for c in all_chapters
    ])

    if sections_per_chapter == 1:
        messages = [
            {"role": "system", "content": "You are a writing structure expert who plans how to write a complete chapter as a single section."},
            {"role": "user", "content": f"""Plan how to write this complete chapter as a single section:

FULL NOVEL CHAPTER PLAN:
{chapter_context}

THIS CHAPTER: Chapter {chapter.number} - {chapter.title}
OPENING SITUATION: {chapter.opening_situation}
CHAPTER GOAL: {chapter.chapter_goal}
CLOSING SITUATION: {chapter.closing_situation}
KEY EVENTS: {', '.join(chapter.key_events)}

Provide the goal and key events for writing this chapter as one section of approximately 1500-2000 words."""},
        ]
    else:
        messages = [
            {"role": "system", "content": f"You are a writing structure expert who breaks chapters into manageable writing sections. You MUST create exactly {sections_per_chapter} sections."},
            {"role": "user", "content": f"""Break this chapter into EXACTLY {sections_per_chapter} sections:

FULL NOVEL CHAPTER PLAN:
{chapter_context}

THIS CHAPTER: Chapter {chapter.number} - {chapter.title}
OPENING SITUATION: {chapter.opening_situation}
CHAPTER GOAL: {chapter.chapter_goal}
CLOSING SITUATION: {chapter.closing_situation}
KEY EVENTS: {', '.join(chapter.key_events)}

Create exactly {sections_per_chapter} sections that progress from the opening to the closing situation.
Each section should be approximately 1500-2000 words when written.

CRITICAL: Create exactly {sections_per_chapter} sections."""},
        ]

    result = chat_structured(messages, SectionPlan, model=OPUS_MODEL)

    if len(result.sections) != sections_per_chapter:
        raise ValueError(f"Requested {sections_per_chapter} sections, got {len(result.sections)}")

    for i, section in enumerate(result.sections):
        section.number = i + 1

    return result
