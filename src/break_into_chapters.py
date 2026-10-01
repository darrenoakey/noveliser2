from brain import chat_structured
from models import ChapterPlan, Character, EnhancedOutline, GeneratedChapterPlan, ScheduleContract
from story_validation import (PremiseGuard, apply_schedule, plan_narrative_text, plan_with_feedback,
                              validate_chapter_plan, validate_plan_against_schedule, validate_premise,
                              with_feedback)


# ##################################################################
# break into chapters
# divide the enhanced outline into detailed chapter plans
def break_into_chapters(enhanced_outline: EnhancedOutline, characters: list[Character],
                        themes: list[str], plot_type: str, num_chapters: int,
                        schedule: ScheduleContract | None = None,
                        premise: PremiseGuard | None = None) -> ChapterPlan:
    character_list = "\n".join([f"- {c.name} ({c.role.value}): {c.biography}" for c in characters])
    theme_list = ", ".join(themes)
    humor_text = "\n".join(f"- {h}" for h in enhanced_outline.humor_elements) if enhanced_outline.humor_elements else "None specified"
    romance_text = "\n".join(f"- {r}" for r in enhanced_outline.romance_elements) if enhanced_outline.romance_elements else "None specified"
    schedule_block = (
        "\nFROZEN SCHEDULE CONTRACT (model-authored and independently validated; NEVER change it):\n"
        + schedule.model_dump_json(indent=2)
        + "\nCopy each scheduled plant_anchor and payoff_anchor exactly into that chapter's key_events. "
          "Use the same physical entity for each plant/payoff. Copy each boundary consequence_anchor "
          "into the next chapter's cause_from_previous. Do not move these events or insert new setup IDs.\n"
        if schedule else ""
    )

    base_messages = [
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
{schedule_block}
For each chapter, provide:
1. TITLE: A compelling chapter title
2. OPENING SITUATION: Where we are at the start (character states, plot situation, setting)
3. CHAPTER GOAL: What this chapter achieves in progressing the overall story
4. CLOSING SITUATION: Where we are at the end (how things have changed)
5. KEY EVENTS: Major plot points and story beats
6. POV CHARACTER: exact name of the cast member whose pursuit drives the chapter
7. CAUSE FROM PREVIOUS: a concrete initiating pressure even for chapter 1 (its status quo/premise); in later chapters name the previous chapter's CONSEQUENCE, not merely the previous chapter's number. Never leave it empty.
8. PURSUIT / OPPOSITION / STAKES: what the POV tries to do, the specific force opposing it, what is lost if it fails
9. CHOICE / COST: the hard choice made and what it irreversibly costs
10. REVERSAL: the reversal or revelation that changes what they believe or must do
11. VALUE BEFORE / VALUE AFTER: a story value (trust, safety, hope, knowledge...) that must be in a DIFFERENT state at the end
12. SETUPS / PAYOFFS: MUST plant at least ONE highly salient promise early and pay it off in a LATER chapter. Use a SHORT ID ONLY like "red-thread" in BOTH lists, no colon, no explanatory text. Its exact concrete object/skill MUST ALSO APPEAR BY NAME IN `key_events` of BOTH plant and payoff chapters: actually show its planting and use. Plant an ID only once; references in intermediate chapters are NOT new setups. Ordinary details are NOT setups. Do not introduce a setup in the final chapter.
13. SUBPLOT / SUBPLOT CHANGE: in EVERY chapter put ONE declared thread's SHORT exact id (e.g. "trust") in `subplot` and say HOW it changes in `subplot_change`. Distribute declared threads so each is advanced in at least one chapter.
14. OPEN QUESTION: nonfinal chapters leave a specific question the reader needs answered next; final chapter state what the reader now knows or what worthwhile future choice remains.
Also give the plan a CENTRAL QUESTION and list 1-2 SUBPLOTS using SHORT identifiers only (e.g. "trust", "ownership"), with no explanations or sentences in the identifier. Every declared subplot must be advanced by at least one chapter (copy the identifier EXACTLY into that chapter's subplot field). Do not leave cause_from_previous or open_question blank in any chapter.
Each chapter must follow from the previous with THEREFORE or BUT, never "and then".

CRITICAL REQUIREMENTS:
- The chapters must cover the ENTIRE story from beginning to end
- Chapters are parts of the whole story, not independent narrative arcs
- Include the themes, plot type, humor and romance elements throughout
- Ensure proper story pacing and character development across all chapters
- The final chapter must provide complete closure and resolution
- No duplication across chapters

Create exactly {num_chapters} chapters."""},
    ]

    prior: GeneratedChapterPlan | None = None

    def build(issues: list[str]) -> ChapterPlan:
        nonlocal prior
        result = chat_structured(with_feedback(base_messages, issues, prior.model_dump_json() if prior else ""),
                                 GeneratedChapterPlan)
        prior = result
        if len(result.chapters) != num_chapters:
            raise ValueError(f"Requested {num_chapters} chapters, got {len(result.chapters)}")
        for i, chapter in enumerate(result.chapters):
            chapter.number = i + 1
        return apply_schedule(result, schedule) if schedule else result

    def validate(plan: ChapterPlan) -> list[str]:
        issues = validate_chapter_plan(plan, characters, num_chapters,
                                       verify_ids_in_events=not bool(schedule))
        if schedule:
            issues.extend(validate_plan_against_schedule(plan, schedule))
        issues.extend(validate_premise(plan_narrative_text(plan), premise))
        return issues

    return plan_with_feedback(build, validate, "chapter plan")
