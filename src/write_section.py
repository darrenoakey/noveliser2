from models import (
    Chapter,
    ChapterPlan,
    Character,
    Section,
    SectionResult,
    WritingStyle,
)
from retrieval_memory import RetrievalMemory

from brain import chat
from story_validation import StoryPlanError, validate_prose, with_feedback
from craft import PROSE_CRAFT, render_character_engine

# how many prior sentences to retrieve as "established details" for a section
RETRIEVAL_K = 12
# bounded rewrites when prose is too thin or contains meta-text; only the accepted text is
# ever returned, so the pipeline embeds into retrieval memory exactly once per accepted section.
MAX_PROSE_ATTEMPTS = 3


def write_section(chapter: Chapter, section: Section, previous_text: str,
                  memory: RetrievalMemory, characters: list[Character],
                  writing_style: WritingStyle, chapter_plan: ChapterPlan,
                  is_final_section: bool) -> SectionResult:
    is_first = chapter.number == 1 and section.number == 1
    section_id = f"ch{chapter.number}.s{section.number}"

    all_chapters_summary = "\n".join([
        f"Chapter {c.number}: {c.title} - {c.chapter_goal} (ends: {c.closing_situation})"
        for c in chapter_plan.chapters
    ])

    position_note = "Begin the story." if is_first else "Continue the narrative from where the previous text ended."
    if is_final_section:
        position_note += " This is the FINAL section. Bring the story to a satisfying conclusion."
    else:
        position_note += " Do NOT conclude or wrap up - there is more story to come after this section."

    previous_context = ""
    if previous_text:
        chars_to_include = min(len(previous_text), 8000)
        previous_context = f"\n\nTEXT SO FAR (last {chars_to_include} characters - continue from here):\n\n{previous_text[-chars_to_include:]}"

    character_block = _render_characters(characters)
    engine_block = render_character_engine(characters)
    scene_directive = _render_scene_directive(section)

    # retrieve the most relevant established details from everything written so
    # far (excluding this section if it is being rewritten on resume).
    query = f"{section.goal}\n{section.key_events}\n" + ", ".join(c.name for c in characters)
    established = memory.retrieve(query, k=RETRIEVAL_K, exclude_section=section_id)
    established_block = _render_established(established)

    issues: list[str] = []
    for _ in range(MAX_PROSE_ATTEMPTS):
        section_text = _generate_prose(
            chapter, section, writing_style, all_chapters_summary,
            position_note, previous_context, character_block, engine_block,
            scene_directive, established_block, issues,
        )
        section_text = _clean_narrative(section_text)
        issues = validate_prose(section_text)
        if not issues:
            return SectionResult(text=section_text, new_facts=[])
    raise StoryPlanError(f"prose for {section_id}", issues, MAX_PROSE_ATTEMPTS)


def _render_scene_directive(section: Section) -> str:
    stype = (section.scene_type or "scene").strip().lower()
    if stype == "sequel":
        body = (
            "This is a SEQUEL (reactive). Move through the POV character's emotional REACTION "
            "to the previous setback, a DILEMMA of bad options, and a DECISION that commits them "
            "to a new goal."
        )
    else:
        body = (
            "This is a SCENE (proactive). The POV character pursues a concrete GOAL, meets "
            "escalating CONFLICT, and ends on a DISASTER that leaves them worse off."
        )
    if section.disaster:
        body += f" The turn this section builds toward: {section.disaster}"
    causal = [
        ("POV character", section.pov_character), ("Forced by", section.cause),
        ("Obstacle", section.obstacle), ("Choice", section.choice), ("Cost", section.cost),
        ("Value shift", f"{section.value_before} -> {section.value_after}" if section.value_before or section.value_after else ""),
        ("Plant (subtly)", ", ".join(section.setups)), ("Pay off", ", ".join(section.payoffs)),
        ("Must hand to next section", section.next_obligation),
    ]
    detail = "; ".join(f"{k}: {v}" for k, v in causal if v)
    if detail:
        body += f" Causal plan - {detail}."
    return f"\n\nSECTION DRAMATIC SHAPE: {body}\n"


def _render_characters(characters: list[Character]) -> str:
    if not characters:
        return "(none defined)"
    lines = []
    for c in characters:
        traits = ", ".join(c.traits) if c.traits else ""
        trait_part = f" — {traits}" if traits else ""
        extras = []
        if c.flaw:
            extras.append(f"flaw: {c.flaw}")
        if c.voice:
            extras.append(f"speaks: {c.voice}")
        if c.relationships:
            extras.append("relationships: " + "; ".join(f"{r.other} ({r.dynamic})" for r in c.relationships))
        extra_part = f" [{' | '.join(extras)}]" if extras else ""
        lines.append(f"- {c.name} ({c.role.value if hasattr(c.role, 'value') else c.role}): {c.biography}{trait_part}{extra_part}")
    return "\n".join(lines)


def _render_established(sentences: list[str]) -> str:
    if not sentences:
        return ""
    bullets = "\n".join(f"- {s}" for s in sentences)
    return (
        "\n\nESTABLISHED DETAILS (drawn from earlier in this same novel — keep your prose "
        "consistent with these; do not contradict them):\n"
        f"{bullets}\n"
    )


def _generate_prose(chapter: Chapter, section: Section, writing_style: WritingStyle,
                    all_chapters_summary: str, position_note: str, previous_context: str,
                    character_block: str, engine_block: str, scene_directive: str,
                    established_block: str, issues: list[str] | None = None) -> str:
    system_content = f"""You are a novelist writing prose fiction. You output ONLY narrative text - no commentary, no meta-discussion, no preamble, no "I'll write..." statements. Just the story itself.

Writing Style: {writing_style.style_description}
Tone: {writing_style.tone}
Voice: {writing_style.voice}
Pacing: {writing_style.pacing}

NOVEL STRUCTURE:
{all_chapters_summary}

{position_note}

CAST (use these exact names and keep each character consistent with their description):
{character_block}{engine_block}

{PROSE_CRAFT}

CRITICAL: Output ONLY the narrative prose. No introductions, no explanations, no section headers. Start immediately with the story text."""

    user_content = f"""CHAPTER: {chapter.number} - {chapter.title}
Chapter Goal: {chapter.chapter_goal}
Chapter Opening: {chapter.opening_situation}
Chapter Closing: {chapter.closing_situation}{_chapter_causal_line(chapter)}

SECTION: {section.number}
Section Goal: {section.goal}
Key Events: {section.key_events}{scene_directive}{established_block}{previous_context}

Write approximately 1500-2000 words of narrative prose for this section.
Maintain continuity with the cast, the established details, and the previous text.
Apply the craft rules above: microtension, show-don't-name, subjective description, sentence-length pacing, and cut the listed prose pitfalls.
Output ONLY the story text. No headers, no commentary, no meta-text. Begin the narrative immediately."""

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
    return chat(with_feedback(messages, issues or []), max_tokens=3500, purpose="prose")


def _chapter_causal_line(chapter: Chapter) -> str:
    parts = [("Forced by", chapter.cause_from_previous), ("Stakes", chapter.stakes),
             ("Choice/cost", f"{chapter.choice} / {chapter.cost}" if chapter.choice or chapter.cost else ""),
             ("Reversal", chapter.reversal), ("Open question to leave", chapter.open_question)]
    text = "; ".join(f"{k}: {v}" for k, v in parts if v)
    return f"\nChapter Causality: {text}" if text else ""


def _clean_narrative(text: str) -> str:
    lines = text.split("\n")
    skip_prefixes = ("i'll ", "i will ", "here's ", "here is ", "continuing ", "let me ")
    cleaned = []
    skipping = True
    for line in lines:
        lower = line.strip().lower()
        if skipping and (not lower or any(lower.startswith(p) for p in skip_prefixes)):
            continue
        skipping = False
        cleaned.append(line)
    return "\n".join(cleaned) if cleaned else text
