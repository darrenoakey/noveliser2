"""Craft directives distilled from docs/unputdownable-fiction.md.

These prompt fragments inject the manual's structural, character, scene, and
prose-level techniques into the generation stages. Each constant is a focused
block written to be dropped straight into a stage's prompt.
"""

from __future__ import annotations

# ##################################################################
# character engine — Wound / Lie / Want vs Need / Truth
# injected into character creation so every major character has a real
# internal engine the prose can dramatize.
CHARACTER_ENGINE_INSTRUCTION = """\
Give every PROTAGONIST and ANTAGONIST a complete internal engine using the
"Lie the Character Believes" framework, and fill these fields for ALL characters
(keep them shorter for minor roles):
- wound: the defining past pain (betrayal, abandonment, humiliation) that taught
  them the world is dangerous.
- lie: the one-sentence false belief they built to survive the wound — logical to
  them, e.g. "I can only rely on myself; vulnerability destroys you."
- want: their concrete EXTERNAL goal in the plot (what they chase).
- need: the INTERNAL truth they must accept to become whole (often the opposite
  of the Lie). The Lie should first look like an asset, then become the main
  obstacle to the Want.
- arc: one of "positive change", "flat", "disillusionment", "corruption".
Make the protagonist's and antagonist's lies thematically mirror each other."""


# ##################################################################
# macro-structure — commercial pacing beats + therefore/but causality
# injected into outline creation.
STRUCTURE_INSTRUCTION = """\
Engineer the outline for commercial, page-turning pacing:
- Open on a vivid status-quo image that earns quick rapport, then hit the
  INCITING INCIDENT early (~10% in).
- Place PLOT POINT ONE near ~25% (locks the protagonist into the central
  conflict), a MIDPOINT reversal / Moment of Truth at ~50% (a glimpse of the
  thematic Truth flips them from reactive to proactive), PLOT POINT TWO at ~75%
  (all seems lost), and the CLIMAX near ~90% where they must sacrifice the WANT
  to embrace the NEED.
- Connect every beat with THEREFORE (causation) or BUT (conflict) — never
  "and then". Each success must trigger a new, worse complication.
- Escalate three major disasters across the middle; let the protagonist's Lie
  cause their setbacks until the Midpoint."""


# ##################################################################
# scene & sequel — micro-structure for section planning
# injected into section breakdown.
SCENE_SEQUEL_INSTRUCTION = """\
Plan each section as either a SCENE or a SEQUEL (alternate them for rhythm):
- A SCENE is proactive: the POV character pursues a concrete GOAL, meets escalating
  CONFLICT, and ends on a DISASTER (a setback that leaves them worse off).
- A SEQUEL is reactive: emotional REACTION to the prior disaster, a DILEMMA of bad
  options, and a DECISION that sets the next section's goal.
For each section set scene_type to "scene" or "sequel" and set disaster to the
specific setback (for a scene) or the hard decision/new-risk (for a sequel) that
ends it. Within a chapter, narrow the protagonist's options as it progresses so
the final section forces a single dangerous path."""


# ##################################################################
# writing style — microtension and pacing philosophy
# injected into style definition.
STYLE_INSTRUCTION = """\
The style must be built for microtension — moment-by-moment suspense from
conflicting emotions, not just plot threat. Specify a voice where dialogue is
compressed and subtextual (characters rarely say what they mean), description is
strictly subjective (only what the POV character notices under their current
emotional state), and sentence length flexes with tension: short, staccato
fragments for action; long, clause-heavy sentences for dread and reflection."""


# ##################################################################
# prose crucible — the line-level rules, injected into the prose prompt.
PROSE_CRAFT = """\
CRAFT RULES — write "unputdownable" prose:
- MICROTENSION: keep moment-to-moment suspense alive through conflicting emotions
  inside the POV character, not just external threat. Every page should make the
  reader uneasy about the next few seconds.
- SHOW, DON'T NAME: never name an emotion ("she felt terrified"). Reconstruct the
  concrete sensory triggers so the reader feels it.
- SUBJECTIVE DESCRIPTION: describe only what the POV character would notice under
  their current emotional duress — never a neutral catalogue.
- DIALOGUE: compressed and subtextual; characters rarely say what they mean; words
  carry an undercurrent battle for control or safety.
- SURPRISINGNESS: juxtapose contrasting emotions (laughter through tears) for
  composite, lingering feeling.
- PACING: short, staccato sentences and fragments for action and threat; long,
  clause-heavy sentences for reflection and dread. Vary sentence length.
- PRESSURE: keep a ticking clock (a literal or figurative deadline) present, and
  let the character's options narrow toward a single dangerous choice.
- CUT THESE: passive voice; qualifiers (very, quite, little, pretty); adverb+weak
  verb pairs (use one precise verb); the word "suddenly"; dummy "there was…";
  "-ing" participle pile-ups; bloated flashbacks; pages of introspection."""


# ##################################################################
# render character engine
# compact per-character Wound/Lie/Want/Need block for the prose prompt, so the
# writer dramatizes each character's internal conflict on the page.
def render_character_engine(characters: list) -> str:
    lines: list[str] = []
    for c in characters:
        bits: list[str] = []
        for label, attr in (("Lie", "lie"), ("Want", "want"), ("Need", "need"), ("Wound", "wound")):
            val = (getattr(c, attr, "") or "").strip()
            if val:
                bits.append(f"{label}: {val}")
        if bits:
            lines.append(f"- {c.name} — " + "; ".join(bits))
    if not lines:
        return ""
    return (
        "\n\nCHARACTER ENGINES (dramatize these internal conflicts through action and "
        "subtext — never state them outright):\n" + "\n".join(lines) + "\n"
    )
