"""Character arc stage.

Given the full cast and the planned plot set (each plot already written as a
standalone story), derive one arc per named character: who they are before, who
they become after, the KIND of change (growth, decline, terminal death, flat,
corruption, redemption), and the step-by-step journey naming which plots force
each change. Downstream stages rely on every cast member having an arc, so any
character the model omits is backfilled with a flat placeholder arc.
"""

from brain import chat_structured
from models import Character, CharacterArc, CharacterArcs, PlotSet


# ##################################################################
# create character arcs
# derive one before/after change arc per character from the plots
def create_character_arcs(characters: list[Character], plots: PlotSet) -> CharacterArcs:
    char_blocks = []
    for c in characters:
        lines = [f"- {c.name} ({c.role.value}): {c.biography}"]
        if c.wound:
            lines.append(f"    wound: {c.wound}")
        if c.lie:
            lines.append(f"    lie: {c.lie}")
        if c.want:
            lines.append(f"    want: {c.want}")
        if c.need:
            lines.append(f"    need: {c.need}")
        char_blocks.append("\n".join(lines))
    cast_str = "\n".join(char_blocks)

    plot_blocks = []
    for p in plots.plots:
        plot_blocks.append(
            f"PLOT: {p.name} ({p.kind})\n"
            f"Premise: {p.premise}\n"
            f"Resolution: {p.resolution}\n"
            f"Story:\n{p.story}"
        )
    plots_str = "\n\n".join(plot_blocks)

    system = (
        "You are a story analyst who traces how a novel's events transform each "
        "character. You are unflinching: characters may grow, decay, be corrupted, "
        "be redeemed, stay the same while the world changes around them, or die."
    )
    user = (
        f"CHARACTERS:\n{cast_str}\n\n"
        f"PLOTS:\n{plots_str}\n\n"
        "Produce EXACTLY ONE arc per named character above. For each arc:\n"
        "- character: the exact name.\n"
        "- before: who they are at the story's start, grounded in their biography.\n"
        "- after: who they are at the end — this MUST follow from what the plots "
        "actually do to them.\n"
        "- change_kind: one of growth, decline, terminal, flat, corruption, "
        "redemption. Use 'terminal' if the character dies — say so plainly. Use "
        "'flat' if they don't change internally while the world changes around them.\n"
        "- journey: how the change happens step by step, naming which plot(s) force "
        "each step."
    )
    result = chat_structured(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        CharacterArcs,
    )

    covered = {a.character.strip().lower() for a in result.arcs}
    for c in characters:
        if c.name.strip().lower() not in covered:
            first_sentence = c.biography.split(".")[0].strip()
            result.arcs.append(
                CharacterArc(
                    character=c.name,
                    before=first_sentence,
                    after="",
                    change_kind="flat",
                    journey="",
                )
            )
    return result
