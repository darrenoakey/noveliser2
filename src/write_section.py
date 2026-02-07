from brain import chat, HAIKU_MODEL
from models import Chapter, Section, SectionResult, WritingStyle, ChapterPlan


# ##################################################################
# write section
# generate the prose for a single section using haiku, with full novel context
def write_section(chapter: Chapter, section: Section, previous_text: str,
                  established_facts: list[str], writing_style: WritingStyle,
                  chapter_plan: ChapterPlan, is_final_section: bool) -> SectionResult:
    is_first = chapter.number == 1 and section.number == 1

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

    facts_text = "\n".join(established_facts[-50:]) if established_facts else "None yet"

    messages = [
        {"role": "system", "content": f"""You are a novelist writing prose fiction. You output ONLY narrative text - no commentary, no meta-discussion, no preamble, no "I'll write..." statements. Just the story itself.

Writing Style: {writing_style.style_description}
Tone: {writing_style.tone}
Voice: {writing_style.voice}
Pacing: {writing_style.pacing}

NOVEL STRUCTURE:
{all_chapters_summary}

{position_note}

CRITICAL: Output ONLY the narrative prose. No introductions, no explanations, no section headers. Start immediately with the story text."""},
        {"role": "user", "content": f"""CHAPTER: {chapter.number} - {chapter.title}
Chapter Goal: {chapter.chapter_goal}
Chapter Opening: {chapter.opening_situation}
Chapter Closing: {chapter.closing_situation}

SECTION: {section.number}
Section Goal: {section.goal}
Key Events: {section.key_events}

ESTABLISHED FACTS:
{facts_text}
{previous_context}

Write approximately 1500-2000 words of narrative prose for this section.
Maintain continuity with established facts and previous text.
Output ONLY the story text. No headers, no commentary, no meta-text. Begin the narrative immediately."""},
    ]
    section_text = chat(messages, model=HAIKU_MODEL)

    section_text = _clean_narrative(section_text)

    fact_messages = [
        {"role": "system", "content": "Extract concrete facts from narrative text. Return ONLY a simple list of facts, one per line. No commentary."},
        {"role": "user", "content": f"""Extract new factual details from this text that should remain consistent:

{section_text[:4000]}

Already known facts:
{facts_text}

List only NEW facts (character descriptions, locations, relationships, objects, timeline events). One per line, no numbering, no explanation."""},
    ]
    fact_response = chat(fact_messages, model=HAIKU_MODEL)
    new_facts = _parse_facts(fact_response)

    return SectionResult(text=section_text, new_facts=new_facts[:10])


# ##################################################################
# clean narrative
# strip any meta-commentary or preamble that the llm prepended to the prose
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


# ##################################################################
# parse facts
# extract clean fact lines from the llm's response
def _parse_facts(response: str) -> list[str]:
    facts = []
    for line in response.split("\n"):
        stripped = line.strip().lstrip("- ").lstrip("* ").strip()
        if stripped and not stripped.lower().startswith(("existing", "already", "known", "note:", "i ")):
            facts.append(stripped)
    return facts
