"""Section prose written by an agentd3 daemon subagent, in tagged form.

The subagent writes each scene as tagged narration and dialogue lines:

    NARRATOR: The rain had not stopped.
    Elena: "Are you coming?"
    NARRATOR: Marcus looked up from the piano.
    Marcus: "In a minute."

The tags let the audio pipeline read speakers directly off the model's own
output — no unreliable post-hoc dialogue attribution. `write_section` strips
the tags to produce clean prose for the EPUB, and also returns the tagged
`lines` so the audio JSON is generated, not parsed.
"""

import logging
import re

from agentd3_client import create_subagent, run_to_completion
from craft import (
    HOUSE_REVISION_BRIEF,
    PROSE_CRAFT,
    render_character_engine,
    render_style_block,
)
from models import (
    Chapter,
    ChapterPlan,
    Character,
    Section,
    SectionResult,
    WritingStyle,
)
from prose_checks import ProseReport, analyse_prose
from retrieval_memory import RetrievalMemory
from sanitize import sanitize_prose

logger = logging.getLogger(__name__)

# a revision is accepted only if its length stays within this ratio of the
# draft, so a "fix" can never quietly drop half the scene
REVISION_LENGTH_RATIO = (0.75, 1.3)

# how much of the accepted, published story is restated at the top of every
# later scene prompt. the subagent's own thread may hold drafts or rejected
# revisions, so this text is the authoritative canon it must continue from.
ACCEPTED_TAIL_CHARS = 6000

# how many prior sentences to retrieve as "established details" for a scene
RETRIEVAL_K = 6

# speaker tag followed by a colon or slash separator, then text. Models that put
# the speaker on its own line leave no separator, so those lines are NOT matched
# here — they fall through to the narrator fold, keeping prose but losing the tag.
_TAG_RE = re.compile(r"^\s*(NARRATOR|[A-Z][A-Za-z'.\- ]{1,40})\s*[:/]\s*(.+?)\s*$")

_SYSTEM_TEMPLATE = """You are a novelist writing one scene of literary fiction, and you also mark up who speaks each line so the scene can be read aloud.

You are NOT an agent, assistant, or orchestrator. Do not read any board, memory, or conversation traffic. Do not take actions, call tools, or respond to anything except the scene-writing request. Your ONLY job is to write story prose in the tagged format below and output nothing else. Never describe what you are doing — just write the story.

Every scene request restates this book's full writing style, character voices and example passages. Follow the version in the latest request.

NOVEL STRUCTURE:
{all_chapters_summary}

CAST (write ONLY about these exact characters, spelled exactly as here — do not invent or substitute any other names):
{character_block}{engine_block}

{craft}

OUTPUT FORMAT — every line is tagged with its speaker. The tag is the speaker name, then a COLON, then a space, then the text, all on ONE line:
- Narration (description, action, internal thought): `NARRATOR: <the narration text>`
- Anything a character says out loud: `<CharacterName>: "<what they say>"`

For example, the exact format is:
NARRATOR: The rain had turned the city into a smear of brake lights.
{speaker_a}: "Are you coming?"
NARRATOR: {speaker_b} looked up from the work in front of them.
{speaker_b}: "In a minute."

CRITICAL RULES:
- Every line MUST start with a speaker tag followed by a colon and a space, all on one line. Never put the speaker on its own line.
- Use ONLY the character names in the CAST above for speakers, spelled exactly. The cast is fixed — never rename, replace, or invent characters.
- One speaker tag per line. Keep each tagged line short — a sentence or two, or one spoken line.
- This story is HEAVY ON DIALOGUE — let the characters talk. Favor spoken exchanges over long narration.
- Every sentence of the scene must be on a tagged line. Do not leave any prose untagged.
- Output ONLY the tagged lines. No headings, no commentary, no untagged prose, no notes about what you are doing. Begin immediately with the first tagged line."""


# ##################################################################
# write section
# build the system prompt once per novel and the short per-scene prompt,
# then delegate the tagged prose to a subagent conversation.
def write_section(
    chapter: Chapter,
    section: Section,
    previous_text: str,
    memory: RetrievalMemory,
    characters: list[Character],
    writing_style: WritingStyle,
    chapter_plan: ChapterPlan,
    is_final_section: bool,
    subagent_id: str | None = None,
    revise: bool = True,
) -> SectionResult:
    is_first = chapter.number == 1 and section.number == 1
    section_id = f"ch{chapter.number}.s{section.number}"

    all_chapters_summary = "\n".join(
        [
            f"Chapter {c.number}: {c.title} - {c.chapter_goal} (ends: {c.closing_situation})"
            for c in chapter_plan.chapters
        ]
    )

    position_note = "Begin the story." if is_first else "Continue the narrative from where the previous scene ended."
    if is_final_section:
        position_note += " This is the FINAL beat — bring the story to a satisfying conclusion."
    else:
        position_note += (
            " Do NOT conclude or wrap up — there is more story to come after this beat. End on a changed"
            " circumstance or decision, with no closing moral, emotional recap or preview of what comes next."
        )

    # established details retrieved from prior prose, for continuity
    query = f"{section.goal}\n{section.key_events}\n" + ", ".join(c.name for c in characters)
    established = memory.retrieve(query, k=RETRIEVAL_K, exclude_section=section_id)
    established_block = _render_established(established)

    character_block = _render_characters(characters)
    engine_block = render_character_engine(characters)

    system_prompt = _SYSTEM_TEMPLATE.format(
        all_chapters_summary=all_chapters_summary,
        character_block=character_block,
        engine_block=engine_block,
        craft=PROSE_CRAFT,
        **_example_speakers(characters),
    )

    style_block = render_style_block(writing_style, characters)
    user_prompt = _build_scene_prompt(
        chapter,
        section,
        position_note,
        established_block,
        is_first,
        characters,
        style_block,
        accepted_tail(previous_text),
    )

    # spin up a subagent the first time, then reuse it for later scenes
    if subagent_id is None:
        subagent_id = create_subagent(
            system_prompt=system_prompt,
            title=f"{chapter.title} - scene {section.number}",
        )

    draft = _scene_from_tagged(run_to_completion(subagent_id, user_prompt))
    final, review = review_scene(subagent_id, draft, writing_style, revise=revise)
    review["writer_subagent_id"] = subagent_id
    logger.info("%s prose review: %s", section_id, review)

    return SectionResult(
        text=final.prose,
        new_facts=[],
        subagent_id=next_subagent_id(subagent_id, review),
        lines=final.lines,
        review=review,
    )


# ##################################################################
# next subagent id
# the conversation the next scene may reuse. after a rejected revision the
# thread's last output is text that was never published, so the next scene
# must start a fresh conversation (which continues from the accepted tail)
# rather than follow rejected canon.
def next_subagent_id(subagent_id: str, review: dict) -> str | None:
    if "revision" in review and not review.get("revised"):
        return None
    return subagent_id


# ##################################################################
# accepted tail
# the end of the published story so far, cut at a paragraph boundary
def accepted_tail(previous_text: str, limit: int = ACCEPTED_TAIL_CHARS) -> str:
    text = (previous_text or "").strip()
    if len(text) <= limit:
        return text
    tail = text[-limit:]
    cut = tail.find("\n\n")
    return tail[cut + 2 :].strip() if 0 <= cut < limit // 2 else tail.strip()


# ##################################################################
# tagged scene
# one version of a scene: its tagged lines, clean prose, and device counts
class TaggedScene:
    def __init__(self, lines: list[dict], prose: str):
        self.lines = lines
        self.prose = prose
        self.report: ProseReport = analyse_prose(prose, dialogue_lines=_dialogue(lines))


# ##################################################################
# scene from tagged
# raw subagent output -> parsed lines, sanitized prose and its report
def _scene_from_tagged(tagged_text: str) -> TaggedScene:
    lines = _parse_tagged(_clean_narrative(tagged_text))
    return TaggedScene(lines, sanitize_prose(_prose_from_lines(lines)))


# ##################################################################
# dialogue
# the spoken lines only, for the counselling-language check
def _dialogue(lines: list[dict]) -> list[str]:
    return [line["text"] for line in lines if line["speaker"] != "NARRATOR"]


# ##################################################################
# review scene
# count repeated devices in the draft; if any review trigger trips, ask the
# same subagent for one targeted revision and keep it only when it really
# lowers the excess without losing length or the tagged format. returns the
# chosen scene and a small record of what happened, stored in the checkpoint.
def review_scene(
    subagent_id: str, draft: TaggedScene, writing_style: WritingStyle, revise: bool = True
) -> tuple[TaggedScene, dict]:
    review = {"draft": draft.report.summary(), "revised": False}
    if not (revise and draft.report.needs_revision):
        return draft, review
    revised = _scene_from_tagged(run_to_completion(subagent_id, build_revision_prompt(draft.report, writing_style)))
    review["revision"] = revised.report.summary()
    if _revision_is_better(draft, revised):
        review["revised"] = True
        return revised, review
    return draft, review


# ##################################################################
# revision is better
# fewer excess devices, a similar length, still tagged lines, and no speaker
# the draft did not already have (a revision must not invent characters)
def _revision_is_better(draft: TaggedScene, revised: TaggedScene) -> bool:
    if not revised.lines or not _speakers(revised) <= _speakers(draft):
        return False
    ratio = revised.report.words / max(1, draft.report.words)
    low, high = REVISION_LENGTH_RATIO
    return low <= ratio <= high and revised.report.excess() < draft.report.excess()


# ##################################################################
# speakers
# the set of speakers in a scene, keyed by lowercased first name so that
# "Elena" and "Elena Marchetti" count as the same character
def _speakers(scene: TaggedScene) -> set[str]:
    return {_speaker_key(line["speaker"]) for line in scene.lines}


# ##################################################################
# speaker key
# lowercased first word of a speaker tag
def _speaker_key(speaker: str) -> str:
    words = speaker.strip().lower().split()
    return words[0] if words else ""


# ##################################################################
# build revision prompt
# targeted edit instructions quoting the scene's own repeated devices
def build_revision_prompt(report: ProseReport, writing_style: WritingStyle) -> str:
    checklist = "\n".join(b for b in (writing_style.revision_brief.strip(), HOUSE_REVISION_BRIEF) if b)
    return f"""REVISION PASS on the scene you just wrote. An editor counted devices that repeat too often in it.
A device's presence alone is not a defect; the problem is automatic repetition. For each quoted sentence, keep it if it earns its place (a practical correction, a deliberate refrain, the scene's strongest beat) and otherwise rewrite it with a perception, physical action or line of subtext specific to this POV character, this place and this moment. Do not add decorative imagery, new facts or backstory, and do not append a moral.

{report.brief()}

Book checklist:
{checklist}

Keep every plot event, every speaker, the order of beats and roughly the same length ({report.words} words).
Change only what these notes require. Output the COMPLETE revised scene in the same tagged format (NARRATOR: / CharacterName: lines), nothing else. Begin immediately."""


# ##################################################################
# example speakers
# the format example uses this book's own cast, so no other book's names leak
def _example_speakers(characters: list[Character]) -> dict:
    names = [c.name for c in characters] + ["Speaker One", "Speaker Two"]
    return {"speaker_a": names[0], "speaker_b": names[1] if len(characters) != 1 else names[2]}


# ##################################################################
# build scene prompt
# short, token-frugal prompt describing exactly this scene and nothing more.
def _build_scene_prompt(
    chapter: Chapter,
    section: Section,
    position_note: str,
    established_block: str,
    is_first: bool,
    characters: list[Character],
    style_block: str,
    accepted: str = "",
) -> str:
    cast_note = _cast_anchor(characters)
    shape = (
        "This is a reactive beat. Move through the POV character's emotional REACTION "
        "to the previous setback, a DILEMMA of bad options, and a DECISION that commits "
        "them to a new goal."
        if (section.scene_type or "").strip().lower() == "sequel"
        else "This is a proactive beat. The POV character pursues a concrete GOAL, meets escalating CONFLICT, and ends on a setback that leaves them worse off."
    )
    disaster = f" The turn this beat builds toward: {section.disaster}" if section.disaster else ""

    prior = "" if is_first else _render_accepted(accepted)

    return f"""CHAPTER: {chapter.number} - {chapter.title}
Chapter goal: {chapter.chapter_goal}

{cast_note}

SCENE GOAL: {section.goal}
KEY BEATS: {section.key_events}
{shape}{disaster}
{position_note}{established_block}{prior}

{style_block}

Write about 1500 words of narrative prose for this scene, as tagged NARRATOR / CharacterName lines.
Output ONLY the tagged lines — no headers, no commentary, no untagged prose. Begin immediately."""


# ##################################################################
# cast anchor
# a short, unambiguous reminder of the canonical cast names, so the model
# cannot drift onto invented characters.
def _cast_anchor(characters: list[Character]) -> str:
    if not characters:
        return ""
    names = " and ".join(c.name for c in characters[:2])
    rest = ", ".join(c.name for c in characters[2:])
    lead = f"Write about {names}"
    if rest:
        lead += f", with {rest}"
    return (
        "CHARACTERS IN THIS SCENE: "
        + ", ".join(c.name for c in characters)
        + ". Use these exact names. "
        + lead + "."
    )


# ##################################################################
# parse tagged
# split the subagent's tagged output into [{"speaker","text"}] lines.
# strips the speaker tag and, for dialogue, the surrounding quotes.
def _parse_tagged(tagged_text: str) -> list[dict]:
    lines: list[dict] = []
    for raw in tagged_text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        match = _TAG_RE.match(line)
        if match:
            speaker = match.group(1).strip()
            text = match.group(2).strip()
            # strip one layer of surrounding quotes from dialogue
            if len(text) >= 2 and text[0] in "\"“'" and text[-1] in "\"”'":
                text = text[1:-1].strip()
            if text:
                lines.append({"speaker": speaker, "text": text})
        else:
            # an untagged line — fold into narrator so no prose is lost
            folded = line.strip()
            if folded and lines and lines[-1]["speaker"] == "NARRATOR":
                lines[-1]["text"] += " " + folded
            elif folded:
                lines.append({"speaker": "NARRATOR", "text": folded})
    return lines


# ##################################################################
# prose from lines
# rebuild clean ebook prose from the tagged lines: dialogue re-quoted,
# narration plain, joined into paragraphs.
def _prose_from_lines(lines: list[dict]) -> str:
    parts = []
    for line in lines:
        speaker = line["speaker"]
        text = line["text"]
        if speaker == "NARRATOR":
            parts.append(text)
        else:
            parts.append(f'"{text}"')
    return "\n\n".join(parts)


# ##################################################################
# render characters
# compact per-character one-liners: name, role, bio, traits.
def _render_characters(characters: list[Character]) -> str:
    if not characters:
        return "(none defined)"
    lines = []
    for c in characters:
        traits = ", ".join(c.traits) if c.traits else ""
        trait_part = f" — {traits}" if traits else ""
        role = c.role.value if hasattr(c.role, "value") else c.role
        lines.append(f"- {c.name} ({role}): {c.biography}{trait_part}")
    return "\n".join(lines)


# ##################################################################
# render accepted
# the published story's ending, which overrides anything else in the thread
def _render_accepted(accepted: str) -> str:
    if not accepted:
        return "\nContinue in the same voice and tagged format."
    return (
        "\n\nACCEPTED STORY SO FAR (the published text, ending exactly where this scene begins. It is the only "
        "canon: if anything earlier in this conversation differs, such as a draft or a revision that was not "
        "used, follow this text. Do not repeat it; continue from its last line in the same voice and tagged "
        f"format):\n<<<\n{accepted}\n>>>"
    )


# ##################################################################
# render established details
def _render_established(sentences: list[str]) -> str:
    if not sentences:
        return ""
    bullets = "\n".join(f"- {s}" for s in sentences)
    return (
        "\n\nESTABLISHED DETAILS (drawn from earlier in this same novel — keep your prose "
        "consistent with these; do not contradict them):\n"
        f"{bullets}\n"
    )


# ##################################################################
# clean narrative
# strip any preamble / meta the subagent may have emitted before the story.
def _clean_narrative(text: str) -> str:
    lines = text.split("\n")
    skip_prefixes = ("i'll ", "i will ", "here's ", "here is ", "continuing ", "let me ", "scene ", "chapter ")
    cleaned = []
    skipping = True
    for line in lines:
        lower = line.strip().lower()
        if skipping and (not lower or any(lower.startswith(p) for p in skip_prefixes)):
            continue
        skipping = False
        cleaned.append(line)
    return "\n".join(cleaned) if cleaned else text
