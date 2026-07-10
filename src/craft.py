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
  cause their setbacks until the Midpoint.
- RAISE THE STAKES every time: each new obstacle must be measurably worse, more
  costly, or more dangerous than the one before it — never a repeat of the same
  size problem. Attach a ticking clock (a real or looming deadline) wherever
  possible so pressure keeps compounding rather than resetting.
- USE DRAMATIC IRONY at least once: let the reader learn something a POV
  character does not yet know (a lie, a threat closing in, another character's
  true motive) so the reader reads on in tension waiting for the character to
  find out."""


# ##################################################################
# chapter hooks — injected into chapter breakdown so every chapter is
# engineered as a page-turner unit, not just a container for events.
CHAPTER_HOOK_INSTRUCTION = """\
Engineer every chapter as its own hook unit:
- CLOSING SITUATION must function as a genuine chapter-ending hook: an
  unresolved question, a fresh threat, a reversal, or a revelation that makes
  a reader want to start the next chapter immediately. Never end a chapter on
  a fully settled, resting beat — leave at least one thread visibly live.
- For CHAPTER 1 specifically, the OPENING SITUATION must be engineered to hook
  from literally the first page: an intriguing action, a strange detail, an
  emotionally loaded moment, or a puzzle — not neutral scene-setting alone.
  The reader should have a question they need answered within a paragraph or
  two."""


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
ends it. Also set intensity to one of "fast" (action, danger, confrontation,
chase, physical peril — should be written lean and quick), "medium" (normal
narrative drive), or "slow" (aftermath, grief, introspection, quiet emotional
processing, tender or reflective beats — should be written more expansively).
Most sequels lean "slow"; most climactic scenes lean "fast". Within a chapter,
narrow the protagonist's options as it progresses so the final section forces a
single dangerous path."""


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
  current emotional state — never a neutral catalogue. When a description risks
  going abstract, back up one step to the actual sensory input that produced it
  ("the granite block fell and squashed the caterpillar," not "the stone fell
  and squashed the bug").
- DIALOGUE: natural and characterful, but layered with subtext; characters rarely
  say exactly what they mean. Let real conversations breathe. Reveal what a
  character is really feeling through CONTRADICTION — what they say versus what
  their body does, or what they claim versus what they actually do next — rather
  than having them state their feelings outright.
- SURPRISINGNESS: juxtapose contrasting emotions (laughter through tears) for
  composite, lingering feeling.
- RHYTHM: VARY sentence length. Most sentences flow at a natural, readable length;
  reserve a short punchy sentence for an occasional peak beat. Variety, not
  fragmentation.
- PRESSURE: keep a quiet ticking clock (a literal or figurative deadline) present.
- CUT THESE (weak-craft habits): passive voice; qualifiers (very, quite, little,
  pretty); adverb+weak verb pairs (use one precise verb); the word "suddenly";
  dummy "there was…"; "-ing" participle pile-ups; bloated flashbacks; pages of
  introspection.
- BANNED PHRASES (measured overused clichés — do NOT use these, find a fresh,
  specific image instead):
  * "the weight of" (and "weighed on", "a weight settled", "heavy with") — a
    single generated novel used "the weight of" 217 times. Never reach for weight
    as a metaphor for emotion or responsibility. Name the concrete thing.
  * "ghost" / "ghosts" as a metaphor for memory or the past ("ghosts of her
    past", "haunted by", "spectral") — measured 245 times in one novel. Banned as
    an emotional metaphor; only literal ghosts in a ghost story are allowed.
  * "breath hitched" / "breath caught" / "sharp intake of breath" / "let out a
    breath she didn't know she was holding" / "held her breath" — the entire
    breath-as-emotion register is exhausted. Show the feeling another way.
  * "heart pounded/hammered/raced/skipped a beat", "stomach dropped/twisted/
    knotted", "pulse quickened", "blood ran cold", "throat tightened" — stock
    autonomic-response clichés. Reconstruct the actual sensation freshly.
- BANNED DESCRIPTION TEMPLATES (stock physical-description scaffolds — a real
  generated novel repeated the eye template in 7+ sections; never use these
  frames, describe the specific person instead):
  * "His/Her eyes were [adjective], [verb]-ing" (e.g. "His eyes were dark,
    searching") and the whole "eyes were X" copula frame.
  * "a mixture of X and Y" / "a combination of X and Y" for a facial expression.
  * "something [flickered/flashed/shifted] in his/her eyes/expression".
  * "couldn't help but", "a shiver ran down her spine", "time seemed to slow",
    "the air was thick with tension", "a moment that felt like an eternity".
- OVERUSED EMOTIONAL-STATE METAPHORS: avoid the generic vocabulary of "a wave of
  [emotion] washed over", "drowning in", "a storm of emotion", "walls she had
  built", "pieces of herself", "a part of her". Anchor every feeling to one
  concrete, character-specific, physical particular rather than a stock abstraction."""


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


# ##################################################################
# voice fingerprint instruction — injected into character creation so every
# character is given a genuinely distinct speaking voice, not a generic one.
CHARACTER_VOICE_INSTRUCTION = """\
Give every character a DISTINCT speaking voice so no two characters sound alike on
the page. Fill these fields for each character (make them genuinely different from
one another — contrast register, rhythm, and habit across the cast):
- voice_register: their vocabulary and diction (e.g. "terse working-class slang",
  "ornate academic formality", "warm folksy plainspokenness", "clinical precision").
- sentence_style: their sentence-length and rhythm tendency in speech (e.g.
  "clipped one-liners", "long winding qualified sentences", "blunt declaratives").
- verbal_tic: a specific, repeatable verbal habit, catchphrase, or filler unique to
  them (e.g. always ends with "right?", over-apologizes, answers questions with
  questions, quotes scripture, never uses contractions). Make it concrete and
  reusable so it can recur in their dialogue."""


# ##################################################################
# render character voice
# formats a single character's dialogue/voice fingerprint into a prompt-ready
# string for the prose writer. Stable signature: takes a Character, returns str.
# Returns "" when the character has no voice fields set (old checkpoints).
def render_character_voice(character) -> str:
    parts: list[str] = []
    for label, attr in (
        ("register", "voice_register"),
        ("sentences", "sentence_style"),
        ("verbal tic", "verbal_tic"),
    ):
        val = (getattr(character, attr, "") or "").strip()
        if val:
            parts.append(f"{label}: {val}")
    if not parts:
        return ""
    name = (getattr(character, "name", "") or "this character").strip() or "this character"
    return f"{name} — " + "; ".join(parts)


# ##################################################################
# word target for scene
# maps a Section's scene_type + intensity to a (min, max) word-count range so
# tense/fast scenes run leaner and reflective/sequel beats run longer, instead of
# a flat target for every section. Stable signature for the later write_section
# integration wave.
def word_target_for_scene(section) -> tuple[int, int]:
    intensity = (getattr(section, "intensity", "") or "").strip().lower()
    scene_type = (getattr(section, "scene_type", "") or "").strip().lower()

    fast_words = {"fast", "tense", "action", "high", "urgent", "quick"}
    slow_words = {"slow", "reflective", "low", "calm", "quiet", "contemplative"}

    if intensity in fast_words:
        return (1100, 1600)
    if intensity in slow_words:
        return (1900, 2500)

    # no explicit/recognized intensity — fall back to scene_type shaping.
    if scene_type == "sequel":
        return (1700, 2200)
    if scene_type == "scene":
        return (1400, 1900)
    return (1500, 2000)


# ##################################################################
# render canon facts
# formats a dict of {entity_attribute: value} into an authoritative "CANON FACTS"
# prompt block. Pure string formatting — no dependencies. Used by the later fact
# ledger + write_section integration wave.
def render_canon_facts(facts: dict[str, str]) -> str:
    items = [(str(k).strip(), str(v).strip()) for k, v in facts.items() if str(v).strip()]
    if not items:
        return ""
    lines = [f"- {k}: {v}" for k, v in items]
    return (
        "\n\nCANON FACTS (do not contradict — these are established and fixed; if a "
        "detail here conflicts with anything else, THESE win):\n" + "\n".join(lines) + "\n"
    )


# ##################################################################
# render name roster
# formats a canonical-spelling reminder block from a list of names. Pure string
# formatting — no dependencies. Used by the later write_section integration wave.
def render_name_roster(names: list[str]) -> str:
    clean = [str(n).strip() for n in names if str(n).strip()]
    # de-duplicate while preserving order
    seen: set[str] = set()
    ordered = [n for n in clean if not (n in seen or seen.add(n))]
    if not ordered:
        return ""
    return (
        "\n\nNAME SPELLINGS (use these EXACT spellings and forms every time — never "
        "abbreviate, contract, or vary them):\n" + ", ".join(ordered) + "\n"
    )
