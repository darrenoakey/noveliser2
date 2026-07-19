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
The style must read as smooth, flowing literary prose — well-formed, varied
sentences in real paragraphs, the kind a reader sinks into. Build in microtension
(moment-by-moment suspense from conflicting emotions, not just plot threat),
subtextual dialogue (characters rarely say exactly what they mean), and subjective
description (what the POV character notices given their current emotional state).
Sentence length should VARY naturally with the moment — most prose is fluid and
grammatically complete; clipped short sentences are an occasional accent for a
peak beat, NOT the default. Do not specify a telegraphic, fragmented, or
sentence-fragment-heavy voice."""


# ##################################################################
# prose crucible — the line-level rules, injected into the prose prompt.
PROSE_CRAFT = """\
CRAFT RULES — write "unputdownable" prose:
- FLOW FIRST: write smooth, immersive literary prose in full, grammatically
  complete sentences and proper paragraphs. This is the default register. Do NOT
  write in clipped fragments, telegraphic bursts, or one-line-per-thought staccato
  as a mannerism — that reads as broken and bizarre.
- MICROTENSION: keep moment-to-moment suspense alive through conflicting emotions
  inside the POV character, not just external threat.
- SHOW, DON'T NAME: never name an emotion ("she felt terrified"). Reconstruct the
  concrete sensory triggers so the reader feels it.
- SUBJECTIVE DESCRIPTION: describe what the POV character would notice given their
  current emotional state — never a neutral catalogue.
- DIALOGUE: natural and characterful, but layered with subtext; characters rarely
  say exactly what they mean. Let real conversations breathe.
- SURPRISINGNESS: juxtapose contrasting emotions (laughter through tears) for
  composite, lingering feeling.
- RHYTHM: VARY sentence length. Most sentences flow at a natural, readable length;
  reserve a short punchy sentence for an occasional peak beat. Variety, not
  fragmentation.
- PRESSURE: keep a quiet ticking clock (a literal or figurative deadline) present.
- CUT THESE: passive voice; qualifiers (very, quite, little, pretty); adverb+weak
  verb pairs (use one precise verb); the word "suddenly"; empty "there was…";
  "-ing" participle pile-ups; bloated flashbacks; pages of introspection."""


# ##################################################################
# render character engine
# compact per-character Wound/Lie/Want/Need block for the prose prompt, so the
# writer dramatizes each character's internal conflict on the page.
def render_character_engine(characters: list) -> str:
    lines: list[str] = []
    for c in characters:
        bits: list[str] = []
        for label, attr in (
            ("Lie", "lie"),
            ("Want", "want"),
            ("Need", "need"),
            ("Wound", "wound"),
        ):
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
