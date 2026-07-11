"""Plot planning stage.

A novel is built from one PRIMARY plot (the protagonist-driven central conflict)
plus a handful of SUBPLOTS anchored to other character relationships and thematic
angles. This module first plans all plot lines in a single structured call, then
writes each one as a complete, satisfying STANDALONE short story — sequentially,
each new story aware of every story already written so they share one consistent
world (same names, relationships, physical facts, timeline). The result is a set
of interlocking plot stories that later pipeline stages weave into the novel.
"""

from brain import chat, chat_structured
from models import Character, Plot, PlotSet


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

    system = (
        "You are a fiction writer producing a complete standalone short story. "
        "The story must be genuinely interesting in itself: a hook opening, "
        "escalating conflict, and a real resolution. Write 600-1000 words of prose "
        "only — no title, no headers, no commentary."
    )
    parts = [
        f"OVERALL NOVEL (for tone only):\n{description}\n",
        "PLOT LINE TO WRITE AS A STORY:\n"
        f"Name: {plot.name}\n"
        f"Premise: {plot.premise}\n"
        f"Stakes: {plot.stakes}\n"
        f"Characters involved: {', '.join(plot.characters_involved)}\n"
        f"Resolution (the story must end here): {plot.resolution}\n",
        f"RELEVANT CHARACTERS:\n{char_lines}\n",
    ]
    if prior_str:
        parts.append(prior_str + "\n")
        parts.append(
            "This story SHARES its world and characters with the plot line(s) "
            "already written above. Nothing may contradict them — names, "
            "relationships, physical facts, and timeline must all agree. Where a "
            "character appears in more than one story, they must feel like the exact "
            "same person.\n"
        )
    parts.append(
        "Write the story now: 600-1000 words, prose only, ending on the stated "
        "resolution."
    )
    user = "\n".join(parts)

    result = chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=2400,
    )
    return result.strip()
