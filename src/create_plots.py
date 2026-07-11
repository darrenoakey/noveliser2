"""Plot planning stage.

A novel is built from one PRIMARY plot (the protagonist-driven central conflict)
plus a handful of SUBPLOTS anchored to other character relationships and thematic
angles. This module first plans all plot lines in a single structured call, then
writes each one as a complete STANDALONE short story — the Anne McCaffrey model:
first the short stories, then the novel fleshes them out. Each story must be
good enough to hand into a story-writing competition on its own: a real hook,
escalating conflict, a satisfying ending, and NO hint that it belongs to
something bigger. Stories are written sequentially, each aware of every story
already written so they share one consistent world (same names, relationships,
physical facts, timeline) — but consistency must never make a story depend on
the others to be understood.
"""

from brain import PROSE_TIER, TIER, chat, chat_structured
from craft import PROSE_CRAFT, render_character_voice
from models import Character, Plot, PlotSet
from write_section import _invalid_prose_reason, _postprocess

# a competition-shaped short story: long enough for a full arc, short enough
# for one generation. The invalid-prose guard's floor is half the low bound.
STORY_WORD_LO = 1800
STORY_WORD_HI = 2600

_STORY_RETRY_INSTRUCTION = (
    "\n\nCRITICAL: Your previous response was invalid — either your own "
    "planning/analysis notes (headers, numbered lists, labels) instead of a story, "
    "or it stopped abruptly mid-sentence far short of the target length. Do not "
    "repeat that mistake. Output ONLY complete, flowing narrative prose at the "
    "requested length, and finish every sentence and the story itself before "
    "stopping."
)


# ##################################################################
# subplot count
# how many subplots a novel of this length should carry
def subplot_count(num_chapters: int) -> int:
    return max(1, min(4, num_chapters // 3))


# ##################################################################
# normalize plots
# ensure a primary exists and sits first, preserving subplot order
def normalize_plots(plots: list[Plot]) -> list[Plot]:
    if not plots:
        return []
    if not any(p.kind == "primary" for p in plots):
        plots[0].kind = "primary"
    primary = [p for p in plots if p.kind == "primary"]
    subplots = [p for p in plots if p.kind != "primary"]
    # if several were marked primary, keep the first as primary, demote the rest
    for extra in primary[1:]:
        extra.kind = "subplot"
    ordered_primary = primary[:1]
    ordered_rest = primary[1:] + subplots
    return ordered_primary + ordered_rest


# ##################################################################
# plan plots
# design the primary plot + subplots in one structured call
def plan_plots(
    description: str,
    plot_type: str,
    themes: list[str],
    characters: list[Character],
    num_chapters: int,
) -> PlotSet:
    n_sub = subplot_count(num_chapters)
    cast_lines = "\n".join(
        f"- {c.name} ({c.role.value}): {c.biography}" for c in characters
    )
    theme_str = ", ".join(themes) if themes else "(none specified)"

    system = (
        "You are a master story architect. You design the interlocking plot lines "
        "of a novel: one central plot plus subplots that deepen theme and character."
    )
    user = (
        f"STORY DESCRIPTION:\n{description}\n\n"
        f"PLOT TYPE: {plot_type}\n"
        f"THEMES: {theme_str}\n\n"
        f"CHARACTERS:\n{cast_lines}\n\n"
        "Design the plot lines for this novel. Produce EXACTLY:\n"
        "- 1 plot with kind=\"primary\": the story's central conflict, driven by the "
        "protagonist.\n"
        f"- {n_sub} plot(s) with kind=\"subplot\": each anchored to a DIFFERENT character "
        "relationship or thematic angle, and each must intersect the primary plot at "
        "least once.\n\n"
        "EVERY plot line must be conceived as a story strong enough to STAND "
        "COMPLETELY ALONE — a premise with its own beginning, escalation, and "
        "satisfying ending that could win a short-story competition by itself, "
        "never a mere thread that only makes sense inside the novel.\n\n"
        "For EVERY plot provide:\n"
        "- name: a short memorable name.\n"
        "- premise: one paragraph — who wants what, and what stands in the way.\n"
        "- stakes: what is lost if this plot fails — concrete and personal, not abstract.\n"
        "- characters_involved: the EXACT names (from the cast above) of the characters "
        "who drive this plot.\n"
        "- resolution: how this plot line ultimately resolves.\n"
        "Leave the 'story' field empty — it is written later."
    )
    result = chat_structured(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        PlotSet,
    )
    if not any(p.kind == "primary" for p in result.plots) and result.plots:
        result.plots[0].kind = "primary"
    result.plots = normalize_plots(result.plots)
    return result


# ##################################################################
# write plot story
# render one plot line as a complete standalone short story
def write_plot_story(
    plot: Plot,
    prior_plots: list[Plot],
    characters: list[Character],
    description: str,
) -> str:
    involved = {n.strip().lower() for n in plot.characters_involved}
    relevant = [
        c for c in characters
        if c.name.strip().lower() in involved
    ] or characters
    char_lines = "\n".join(f"- {c.name}: {c.biography}" for c in relevant)

    prior_blocks = []
    for prev in prior_plots:
        prior_blocks.append(
            "PREVIOUSLY WRITTEN PLOT LINE (must stay consistent with this — same "
            "world, same character facts, no contradictions):\n"
            f"Name: {prev.name}\n"
            f"Resolution: {prev.resolution}\n"
            f"Story:\n{prev.story}"
        )
    prior_str = "\n\n".join(prior_blocks)

    voices = [render_character_voice(c) for c in relevant]
    voice_lines = "\n".join(v for v in voices if v)
    voice_block = f"\nCHARACTER VOICES (keep each distinct):\n{voice_lines}\n" if voice_lines else ""

    system = (
        "You are an award-winning short-story writer. You are producing a COMPLETE, "
        "SELF-CONTAINED short story good enough to submit to a story-writing "
        "competition as-is. Requirements:\n"
        "- A hook opening that earns attention within the first two sentences.\n"
        "- Escalating conflict through the middle — every scene raises the cost.\n"
        "- A genuinely satisfying ENDING that resolves the story's own question. The "
        "reader must close it feeling they read a whole story, not an excerpt.\n"
        "- ZERO hints that this belongs to anything bigger: no unresolved threads, no "
        "cliffhangers, no references a reader without other context wouldn't follow, "
        "no sequel bait.\n"
        "- Entertaining, immersive prose a competition judge would rank highly.\n\n"
        + PROSE_CRAFT
        + f"\n\nWrite {STORY_WORD_LO}-{STORY_WORD_HI} words of prose only — no title, "
        "no headers, no commentary."
    )
    parts = [
        f"SETTING / WORLD (for flavor only — the story must stand alone):\n{description}\n",
        "THE STORY TO WRITE:\n"
        f"Name (do not print it): {plot.name}\n"
        f"Premise: {plot.premise}\n"
        f"Stakes: {plot.stakes}\n"
        f"Characters involved: {', '.join(plot.characters_involved)}\n"
        f"Resolution (the ending must land here, fully resolved): {plot.resolution}\n",
        f"CHARACTERS:\n{char_lines}\n{voice_block}",
    ]
    if prior_str:
        parts.append(prior_str + "\n")
        parts.append(
            "This story SHARES its world and characters with the story/stories above. "
            "Nothing may contradict them — names, relationships, physical facts, and "
            "timeline must all agree; a character appearing in more than one story "
            "must feel like the exact same person. BUT consistency must never create "
            "dependence: this story must read as complete and fully understandable to "
            "someone who has never seen the others.\n"
        )
    parts.append(
        f"Write the story now: {STORY_WORD_LO}-{STORY_WORD_HI} words, prose only, a "
        "complete standalone story ending on the stated resolution."
    )
    user = "\n".join(parts)

    def _valid(raw: str) -> bool:
        return _invalid_prose_reason(_postprocess(raw), STORY_WORD_LO) is None

    def _generate(extra: str, tier) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user + extra},
        ]
        return _postprocess(chat(messages, max_tokens=12288, tier=tier, validate=_valid))

    # draft on the escalated prose tier, with the same bounded retry/fallback
    # discipline as section prose: one reinforced same-tier retry, one
    # non-reasoning-tier fallback, then fail loudly — never keep broken text.
    story = _generate("", PROSE_TIER)
    defect = _invalid_prose_reason(story, STORY_WORD_LO)
    if defect:
        story = _generate(_STORY_RETRY_INSTRUCTION, PROSE_TIER)
        defect = _invalid_prose_reason(story, STORY_WORD_LO)
        if defect:
            story = _generate(_STORY_RETRY_INSTRUCTION, TIER)
            defect = _invalid_prose_reason(story, STORY_WORD_LO)
            if defect:
                raise ValueError(f"plot story '{plot.name}': {defect} after two retries")

    return _revise_story(story).strip()


# ##################################################################
# revise story
# one bounded competition-polish pass: critique-and-edit against a standalone
# short-story rubric. Never a wholesale rewrite; falls back to the draft when
# the revision itself comes back broken.
def _revise_story(draft: str) -> str:
    floor = max(1, len(draft.split()) // 2)

    def _valid(raw: str) -> bool:
        return _invalid_prose_reason(_postprocess(raw), floor) is None

    system = (
        "You are a short-story competition judge turned line editor. You make "
        "TARGETED edits to the story below — you do NOT rewrite it wholesale or "
        "change its events. Output ONLY the edited story, no commentary.\n\n"
        + PROSE_CRAFT
    )
    user = (
        "Edit this story so it would score at the top of a competition:\n"
        "- HOOK: the first two sentences must seize attention.\n"
        "- COMPLETENESS: the ending must resolve the story's own question fully — "
        "remove or resolve any dangling thread, cliffhanger, or outward reference "
        "that assumes context a standalone reader lacks.\n"
        "- SHOW don't TELL, cut clichés, sharpen dialogue (see craft rules above).\n\n"
        f"STORY:\n{draft}\n\n"
        "Output the edited story now, and nothing else."
    )
    try:
        revised = _postprocess(chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=12288, tier=PROSE_TIER, validate=_valid,
        ))
    except Exception:
        return draft
    if _invalid_prose_reason(revised, floor):
        return draft
    return revised
