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
# writing style — what a style definition must pin down
# injected into style definition. asks for concrete, checkable decisions
# (distance, per-character diction, rhythm, where images come from, worked
# examples, a revision brief) rather than adjectives like "lyrical".
STYLE_INSTRUCTION = """\
The style must read as smooth, flowing literary prose: varied, grammatically
complete sentences in real paragraphs, the kind a reader sinks into. Build in
microtension (moment-by-moment suspense from conflicting emotions, not only plot
threat), subtextual dialogue (characters rarely say exactly what they mean), and
subjective description (what the POV character notices given their current state).
Clipped short sentences are an occasional accent for a peak beat, never the
default. Do not specify a telegraphic or fragment-heavy voice.

Every field must be a concrete decision a writer could follow and an editor could
check. Adjectives alone ("lyrical", "evocative", "atmospheric") are not a style.
- narrative_distance: whose head we are in, how close (can the narration use the
  POV character's own slang and judgements?), when the camera pulls back (scene
  transitions, time skips) and when it pushes in (peaks).
- character_voices: one entry per speaking character. Diction drawn from their
  job, age, region, class and history; their sentence habits (short and blunt,
  long and qualified, questions instead of answers); how they dodge a painful
  subject; words they would never use. Two characters must not sound alike.
- rhythm: how sentence and paragraph length move with the action, what a long
  sentence is for in this book, and how a paragraph usually ends (on an action,
  an image or a line of dialogue, not a moral).
- imagery_sources: the specific worlds this book's comparisons come from (each
  POV character's trade, landscape, era, obsessions), with three or four example
  source domains per POV character, and the stock images this setting tempts a
  writer toward that must be avoided.
- positive_examples: three or four original passages of two to five sentences,
  written in this book's style about this book's people, each showing a
  different skill: an image taken from the POV character's world, dialogue with
  subtext in two distinct voices, a long sentence of action followed by a short
  one, a scene ending on a concrete action.
- revision_brief: a short checklist an editor would run over each finished scene
  for this book in particular."""


# ##################################################################
# house narrative distance
# the default point-of-view discipline used when a style leaves it vague.
HOUSE_NARRATIVE_DISTANCE = """\
Hold close third person by default: the narration may borrow the POV character's
vocabulary, opinions and blind spots, and it knows only what they know. Pull the
camera back for transitions and passing time, in a sentence or two of summary,
then come straight back in. Push closest at the peaks, where narration and
thought merge. Never step outside the POV character to explain what a moment
meant, and never name a feeling the scene has already shown."""


# ##################################################################
# house dialogue and diction
# how characters must sound when the style gives no per-character voice.
HOUSE_DIALOGUE = """\
Each character speaks from their own life: their trade, age, region and history
decide their nouns and verbs. In every exchange each speaker wants something
private and concrete, often while doing a physical task, and one of them usually
holds more power. People interrupt, deflect, answer the question
they wish they had been asked, go quiet, change the subject to something
practical. Feelings come out sideways through an argument about the dishes or
the route, rarely as a statement. Characters do not talk like counsellors or
self-help books ("I hear you", "that's valid", "you don't have to carry this
alone", "I need you to know") unless that register is the character, and then
another character should notice it. Not every exchange needs a quotable line
or a reconciliation: allow banal, practical, misheard and unfinished lines.
Never let two characters share the same rhythm, vocabulary or tidy eloquence,
and never fake a voice with dialect spellings or catchphrases."""


# ##################################################################
# house rhythm
# sentence and paragraph movement.
HOUSE_RHYTHM = """\
Let sentence length follow the action: a long sentence can carry a run of
movement joined by "and", a short one lands a fact. Do not put sentences of the
same shape side by side, and do not start consecutive sentences with the same
word unless the repetition is the point. Vary paragraph length too. End a
paragraph on something that happens, is seen or is said, not on a summary of
what it meant."""


# ##################################################################
# house image sourcing
# where comparisons may come from.
HOUSE_IMAGERY = """\
Take every comparison from the POV character's own world: what they do with
their hands, where they grew up, what they fear, what they would notice first.
Ask whether this person, at this moment, would think of this comparison; if not,
cut it or use the literal detail. Prefer the literal, exact detail to a figure, and
never stack images from different domains in one emotional beat; let one image
develop instead. Avoid images that could
sit in any book: silence that stretches, air that thickens or hangs, weight that
settles, something that shifts, a breath held without knowing, a hum, ozone,
a smile that does not reach the eyes."""


# ##################################################################
# house pattern budget
# rhetorical devices that are fine in moderation and grating on repeat. the
# fault is automatic, repeated use, not the device itself, so these are
# budgets, not bans.
HOUSE_PATTERN_BUDGET = """\
These devices are legitimate but wear thin when repeated on autopilot. Use each
only where it earns its place (a ceremony, an obsession, a real argument, a
practical correction such as "Not the north stair. The west one."), and rarely
twice in a scene:
- lists of three ("frozen, amber, slightly unreal"; "kitchen, broadcast,
  lights") and three short parallel sentences in a row. Use the natural number
  of items; two or four is often truer.
- contrast framing: "not X, but Y", "It wasn't fear. It was something else.",
  "not because X but because Y", "less X than Y". Say what the thing is.
- em dashes. Use commas, full stops or a new sentence; keep the dash for speech
  that is cut off.
- a paragraph that ends by explaining itself ("and that was the point", "for
  the first time in years", "maybe that was enough").
- stock phrasing: "hung in the air", "the weight of", "something shifted",
  "a beat", "let out a breath", "jaw tightened", "the silence stretched",
  "a flicker of", "palpable", "testament", "tapestry", "delve".
- narration that names the emotion after showing it ("she felt a surge of
  fear", "he realized he was angry")."""


# ##################################################################
# house positive examples
# original sample passages showing the target register, used when a book's
# style supplies none and alongside its own examples otherwise.
HOUSE_EXAMPLES = [
    ("Nell heard the engine miss before anyone else on deck did, a hitch in the third cylinder like a man "
    "putting his weight on a loose stair. She kept coiling the stern line. If she ran, the passengers would "
    "look up from their phones, and the captain would ask her in front of all of them what she had forgotten "
    "to check that morning."),
    ('"You kept the coat," her father said. "It was warm." "It was mine." She hung it on the hook by the door '
    "and went to fill the kettle, and he watched her stop at the line he had painted on the inside of it "
    "years ago, a thing she had forgotten he had done."),
    ("The road out of Carrow went down through the quarry cut in long switchbacks, and on every turn the "
    "driver leaned into the wheel and swore at a slope he had driven each weekday since the quarry closed. "
    "Tomas counted the turns. On the ninth the driver stopped swearing."),
    ("The ringer's daughter could read weather in the rope. Rain made it heavy and slow to come back to her "
    "hands, and frost made it jump. This morning it jumped, and she let it burn through her palms rather "
    "than stop, because the town counted the strokes and a short count meant a death."),
]


# ##################################################################
# house revision brief
# the editor's checklist each scene is held to.
HOUSE_REVISION_BRIEF = """\
- Does every simile come from the POV character's world? Replace the rest with literal detail.
- Do any two speakers sound alike? Rewrite one in their own diction.
- Does any character explain their feelings in tidy, counselling language? Make them dodge, act or change the subject.
- Count the lists of three, "not X but Y" turns and em dashes; keep the best one of each, rewrite the others.
- Does any paragraph end on a moral or summary? End it on an action, image or spoken line instead.
- Are three sentences in a row the same length or shape? Join two or cut one."""


# ##################################################################
# prose crucible — the line-level rules, injected into the prose prompt.
PROSE_CRAFT = """\
CRAFT RULES — write "unputdownable" prose:
- FLOW FIRST: write smooth, immersive literary prose in full, grammatically
  complete sentences and proper paragraphs. This is the default register. Do NOT
  write in clipped fragments, telegraphic bursts, or one-line-per-thought staccato
  as a mannerism.
- MICROTENSION: keep moment-to-moment suspense alive through conflicting emotions
  inside the POV character, not just external threat.
- SHOW, DON'T NAME: avoid naming an emotion ("she felt terrified"). Give the
  concrete sensory triggers and the action they cause so the reader feels it.
- SUBJECTIVE DESCRIPTION: describe what the POV character would notice given their
  current emotional state, never a neutral catalogue.
- DIALOGUE: characterful and layered with subtext; characters rarely say exactly
  what they mean. Let real conversations breathe.
- SURPRISINGNESS: juxtapose contrasting emotions (laughter through tears) for
  composite, lingering feeling.
- TACTILE DESCRIPTION: prefer concrete, physical, sensory detail (what the POV
  character sees, hears, smells, touches) over abstract summary.
- PRESSURE: keep a quiet ticking clock (a literal or figurative deadline) present.
- GRAMMAR: every sentence must be grammatically complete. Never break a word,
  never drop a space between sentences, never restart a word in capitals.
- PLACEHOLDERS: if you need a name, number, or term you do not have, invent a
  concrete one inline. Never write a bracketed placeholder like "[name]".
- CUT THESE: needless passive voice; qualifiers (very, quite, pretty); adverb plus
  weak verb (use one precise verb); "suddenly"; empty "there was"; "-ing"
  participle pile-ups; bloated flashbacks; pages of introspection.

PATTERN BUDGET:
""" + HOUSE_PATTERN_BUDGET


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


# ##################################################################
# render style block
# the complete style for one book as a prompt block: the book's own choices
# first, the house rules for anything the book leaves blank, then every
# example passage. injected into every scene prompt so a resumed subagent or
# an old checkpoint still writes to the full style.
def render_style_block(style, characters: list | None = None) -> str:
    parts = [
        "WRITING STYLE FOR THIS BOOK (follow all of it in every scene):",
        _labelled("Style", style.style_description),
        _labelled("Tone", style.tone),
        _labelled("Voice", style.voice),
        _labelled("Pacing", style.pacing),
        _labelled("Narrative distance", style.narrative_distance or HOUSE_NARRATIVE_DISTANCE),
        _render_voices(style.character_voices, characters),
        _labelled("Rhythm", style.rhythm or HOUSE_RHYTHM),
        _labelled("Imagery", (style.imagery_sources + "\n" if style.imagery_sources else "") + HOUSE_IMAGERY),
        _render_examples(list(style.examples) + list(style.positive_examples)),
        _labelled("Revision checklist", (style.revision_brief + "\n" if style.revision_brief else "") + HOUSE_REVISION_BRIEF),
    ]
    return "\n\n".join(p for p in parts if p)


# ##################################################################
# labelled
# one "Label: text" paragraph, or nothing when the text is blank
def _labelled(label: str, text: str) -> str:
    text = (text or "").strip()
    return f"{label}:\n{text}" if text else ""


# ##################################################################
# render voices
# per-character diction lines, plus the house dialogue rules. cast members
# with no voice entry are listed so the writer derives one from their sheet.
def _render_voices(voices: list, characters: list | None) -> str:
    lines = [_voice_line(v) for v in voices]
    named = {v.name.strip().lower() for v in voices}
    missing = [c.name for c in characters or [] if c.name.strip().lower() not in named]
    if missing:
        lines.append(
            "- " + ", ".join(missing) + ": no voice sheet yet; derive diction from their biography and keep "
            "it distinct from everyone else."
        )
    body = "\n".join(lines)
    return _labelled("Character voices", (body + "\n" if body else "") + HOUSE_DIALOGUE)


# ##################################################################
# voice line
# one character's voice sheet on a single line
def _voice_line(voice) -> str:
    bits = [b for b in (voice.diction, voice.dialogue_habits) if b and b.strip()]
    if voice.never_says and voice.never_says.strip():
        bits.append("never says: " + voice.never_says.strip())
    label = voice.name.strip() or "Another speaker"
    return f"- {label}: " + "; ".join(b.strip() for b in bits)


# ##################################################################
# render examples
# the book's example passages followed by the house passages, all quoted in
# full so the writer imitates register rather than reading a description of it
def _render_examples(examples: list[str]) -> str:
    book = [e.strip() for e in examples if e and e.strip()]
    lines = ["Passages in this book's register (imitate the craft, never copy the words):"]
    lines += [f"- {e}" for e in book]
    lines.append("General register examples from other stories (craft only, never reuse their people or events):")
    lines += [f"- {e}" for e in HOUSE_EXAMPLES]
    return "\n".join(lines)
