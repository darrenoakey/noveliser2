from brain import chat, chat_structured
from fact_ledger import FactLedger
from models import (
    Chapter,
    ChapterPlan,
    Contradiction,
    FactDelta,
    Section,
    SectionResult,
    WritingStyle,
)

MAX_CONTRADICTION_RETRIES = 2


def write_section(chapter: Chapter, section: Section, previous_text: str,
                  ledger: FactLedger, writing_style: WritingStyle,
                  chapter_plan: ChapterPlan, is_final_section: bool) -> SectionResult:
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

    canon_block = ledger.render_for_prompt()
    contradiction_directive = ""

    section_text = ""
    last_contradictions: list[Contradiction] = []

    for _ in range(MAX_CONTRADICTION_RETRIES + 1):
        section_text = _generate_prose(
            chapter, section, writing_style, all_chapters_summary,
            position_note, previous_context, canon_block, contradiction_directive,
        )
        section_text = _clean_narrative(section_text)

        delta = _extract_delta(section_text, ledger, section_id)
        last_contradictions = delta.contradictions

        if not last_contradictions:
            added = ledger.add_all(delta.new_facts)
            return SectionResult(text=section_text, new_facts=added)

        contradiction_directive = _build_contradiction_directive(last_contradictions)

    raise ValueError(
        f"Section {section_id} could not be written without contradicting established canon "
        f"after {MAX_CONTRADICTION_RETRIES + 1} attempts. Contradictions: "
        + "; ".join(_format_contradiction(c) for c in last_contradictions)
    )


def _generate_prose(chapter: Chapter, section: Section, writing_style: WritingStyle,
                    all_chapters_summary: str, position_note: str, previous_context: str,
                    canon_block: str, contradiction_directive: str) -> str:
    system_content = f"""You are a novelist writing prose fiction. You output ONLY narrative text - no commentary, no meta-discussion, no preamble, no "I'll write..." statements. Just the story itself.

Writing Style: {writing_style.style_description}
Tone: {writing_style.tone}
Voice: {writing_style.voice}
Pacing: {writing_style.pacing}

NOVEL STRUCTURE:
{all_chapters_summary}

{position_note}

ESTABLISHED CANON (these facts are TRUE and IMMUTABLE - your prose MUST be consistent with them; never contradict any value below):
{canon_block}

CRITICAL: Output ONLY the narrative prose. No introductions, no explanations, no section headers. Start immediately with the story text."""

    user_content = f"""CHAPTER: {chapter.number} - {chapter.title}
Chapter Goal: {chapter.chapter_goal}
Chapter Opening: {chapter.opening_situation}
Chapter Closing: {chapter.closing_situation}

SECTION: {section.number}
Section Goal: {section.goal}
Key Events: {section.key_events}
{contradiction_directive}{previous_context}

Write approximately 1500-2000 words of narrative prose for this section.
Maintain continuity with the established canon and previous text.
Output ONLY the story text. No headers, no commentary, no meta-text. Begin the narrative immediately."""

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
    return chat(messages, max_tokens=2400)


def _extract_delta(section_text: str, ledger: FactLedger, section_id: str) -> FactDelta:
    canon_block = ledger.render_for_prompt()
    known = ledger.known_subjects()
    if known:
        known_subjects_block = (
            "KNOWN SUBJECTS (use these EXACT names if the passage refers to them; "
            "do NOT introduce a near-duplicate like 'Clara Whitty' when 'Clara Whitby' is already known):\n  - "
            + "\n  - ".join(known)
        )
    else:
        known_subjects_block = "KNOWN SUBJECTS: (none yet)"

    messages = [
        {"role": "system", "content": (
            "You are a continuity editor. You compare a newly written passage of a novel against an established canon "
            "of facts and report two things:\n"
            "  1. NEW canonical facts established by the passage (subject + attribute + short value).\n"
            "  2. CONTRADICTIONS: places where the passage states a value for a subject's attribute that conflicts "
            "with the established canon.\n\n"
            "Rules:\n"
            "- Use snake_case attribute names like 'breed', 'eye_color', 'hair_color', 'occupation', 'location', "
            "'age', 'owner'.\n"
            "- Keep values short (a phrase, not a sentence).\n"
            "- For subjects, ALWAYS use the canonical name from the KNOWN SUBJECTS list when the passage refers to "
            "the same entity. Do not invent variants or near-duplicates.\n"
            "- Do NOT emit trivial name facts: never set attribute='first_name'/'last_name'/'name'/'full_name' when "
            "the value is already part of the subject (e.g. subject='Clara Whitby', attribute='first_name', "
            "value='Clara' is FORBIDDEN — skip it).\n"
            "- Treat semantically equivalent values as equal (e.g. 'golden retriever' == 'Golden Retriever'). "
            "Only flag a contradiction when the values genuinely conflict.\n"
            "- Restating an existing canon fact is NOT a new fact and NOT a contradiction.\n"
            "- Subjective descriptions, atmosphere, and emotions are NOT facts. Only durable physical / "
            "biographical / relational attributes count.\n"
            "- For each contradiction, include a short verbatim quote from the passage."
        )},
        {"role": "user", "content": f"""{known_subjects_block}

ESTABLISHED CANON:
{canon_block}

PASSAGE (section {section_id}):
{section_text}

Return your analysis as structured JSON."""},
    ]

    delta = chat_structured(messages, FactDelta)
    if not isinstance(delta, FactDelta):
        delta = FactDelta(**delta.model_dump())  # type: ignore[arg-type]

    canonicalized_new = []
    for fact in delta.new_facts:
        canonical = ledger.canonical_subject(fact.subject)
        if canonical and canonical != fact.subject:
            fact = fact.model_copy(update={"subject": canonical})
        if not fact.first_seen:
            fact.first_seen = section_id
        canonicalized_new.append(fact)
    delta.new_facts = canonicalized_new

    delta.contradictions = _verify_contradictions(delta.contradictions, ledger)
    return delta


def _verify_contradictions(reported: list[Contradiction], ledger: FactLedger) -> list[Contradiction]:
    verified = []
    for contra in reported:
        canonical_subject = ledger.canonical_subject(contra.existing.subject) or contra.existing.subject
        existing = ledger.get(canonical_subject, contra.existing.attribute)
        if existing is None:
            continue
        if existing.value.strip().lower() == contra.new_value.strip().lower():
            continue
        verified.append(Contradiction(existing=existing, new_value=contra.new_value, quote=contra.quote))
    return verified


def _build_contradiction_directive(contradictions: list[Contradiction]) -> str:
    bullets = "\n".join(f"  - {_format_contradiction(c)}" for c in contradictions)
    return (
        "\n\nCANON VIOLATIONS IN YOUR PREVIOUS DRAFT - YOU MUST FIX THESE. "
        "Rewrite the section so the prose is consistent with the established canon:\n"
        f"{bullets}\n"
    )


def _format_contradiction(c: Contradiction) -> str:
    quote = f' (you wrote: "{c.quote}")' if c.quote else ""
    return (
        f"{c.existing.subject}.{c.existing.attribute} is '{c.existing.value}', "
        f"NOT '{c.new_value}'{quote}"
    )


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
