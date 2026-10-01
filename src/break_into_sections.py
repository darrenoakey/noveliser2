from brain import chat_structured
from craft import SCENE_SEQUEL_INSTRUCTION
from models import Chapter, Character, SectionPlan, GeneratedSectionPlan
from story_validation import plan_with_feedback, validate_section_plan, with_feedback


# ##################################################################
# break into sections
# divide a chapter into writing-sized sections with clear goals
def break_into_sections(chapter: Chapter, sections_per_chapter: int, all_chapters: list[Chapter],
                        characters: list[Character] | None = None) -> SectionPlan:
    chapter_context = "\n".join([
        f"  Ch {c.number}: {c.title} - {c.chapter_goal}"
        for c in all_chapters
    ])

    chapter_causal = _render_chapter_causal(chapter)
    cast_names = ", ".join(c.name for c in characters or [])
    section_contract = SECTION_CAUSAL_INSTRUCTION.format(cast=cast_names or "(any cast member)")

    if sections_per_chapter == 1:
        base_messages = [
            {"role": "system", "content": "You are a writing structure expert who plans how to write a complete chapter as a single section."},
            {"role": "user", "content": f"""Plan how to write this complete chapter as a single section:

FULL NOVEL CHAPTER PLAN:
{chapter_context}

THIS CHAPTER: Chapter {chapter.number} - {chapter.title}
OPENING SITUATION: {chapter.opening_situation}
CHAPTER GOAL: {chapter.chapter_goal}
CLOSING SITUATION: {chapter.closing_situation}
KEY EVENTS: {', '.join(chapter.key_events)}
{chapter_causal}

Provide the goal and key events for writing this chapter as one section of approximately 1500-2000 words.

{section_contract}"""},
        ]
    else:
        base_messages = [
            {"role": "system", "content": f"You are a writing structure expert who breaks chapters into manageable writing sections. You MUST create exactly {sections_per_chapter} sections."},
            {"role": "user", "content": f"""Break this chapter into EXACTLY {sections_per_chapter} sections:

FULL NOVEL CHAPTER PLAN:
{chapter_context}

THIS CHAPTER: Chapter {chapter.number} - {chapter.title}
OPENING SITUATION: {chapter.opening_situation}
CHAPTER GOAL: {chapter.chapter_goal}
CLOSING SITUATION: {chapter.closing_situation}
KEY EVENTS: {', '.join(chapter.key_events)}
{chapter_causal}

Create exactly {sections_per_chapter} sections that progress from the opening to the closing situation.
Each section should be approximately 1500-2000 words when written.

{SCENE_SEQUEL_INSTRUCTION}

{section_contract}

CRITICAL: Create exactly {sections_per_chapter} sections."""},
        ]


    prior: GeneratedSectionPlan | None = None

    def build(issues: list[str]) -> SectionPlan:
        nonlocal prior
        result = chat_structured(with_feedback(base_messages, issues, prior.model_dump_json() if prior else ""),
                                 GeneratedSectionPlan)
        prior = result
        if len(result.sections) != sections_per_chapter:
            raise ValueError(f"Requested {sections_per_chapter} sections, got {len(result.sections)}")
        for i, section in enumerate(result.sections):
            section.number = i + 1
        return result

    if characters is None:
        return build([])
    prior_setups = [s for c in all_chapters if c.number < chapter.number for s in c.setups]
    return plan_with_feedback(
        build,
        lambda plan: validate_section_plan(plan, chapter, characters, sections_per_chapter, prior_setups),
        f"section plan for chapter {chapter.number}",
    )


SECTION_CAUSAL_INSTRUCTION = """For EVERY section also fill in the causal contract:
- pov_character: exact name from the cast ({cast})
- cause: for the first section, pressure from the chapter opening; otherwise the specific previous section consequence. NEVER leave empty.
- obstacle: the specific opposition met; choice and cost: the decision made and what it costs
- value_before / value_after: the story value must be in a DIFFERENT state at the end
- setups / payoffs: ids of clues planted here; payoffs may only cite setups planted in earlier chapters or earlier sections of this chapter
- next_obligation: for nonfinal sections, what the next must address; for the final section, what the NEXT CHAPTER must address or how the novel's final question was answered. NEVER leave empty.
Sections chain by THEREFORE/BUT, never "and then"."""


def _render_chapter_causal(chapter: Chapter) -> str:
    parts = [
        ("POV", chapter.pov_character), ("CAUSE FROM PREVIOUS", chapter.cause_from_previous),
        ("PURSUIT", chapter.pursuit), ("OPPOSITION", chapter.opposition), ("STAKES", chapter.stakes),
        ("CHOICE", chapter.choice), ("COST", chapter.cost), ("REVERSAL", chapter.reversal),
        ("VALUE", f"{chapter.value_before} -> {chapter.value_after}" if chapter.value_before or chapter.value_after else ""),
        ("SETUPS TO PLANT", ", ".join(chapter.setups)), ("PAYOFFS DUE", ", ".join(chapter.payoffs)),
        ("SUBPLOT", chapter.subplot), ("OPEN QUESTION", chapter.open_question),
    ]
    return "\n".join(f"{k}: {v}" for k, v in parts if v)
