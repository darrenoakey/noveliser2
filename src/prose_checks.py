"""Review triggers for repeated rhetorical habits in generated scenes.

Lists of three, "not X but Y" contrasts, em dashes, stock phrases, counselling
language in dialogue and paragraphs that end on a moral are all ordinary
human rhetoric. What reads as machine-made is their automatic repetition, so
nothing here bans a device. Each check counts occurrences, normalises by word
count, and trips only when a scene uses a device well beyond the rate measured
in published human fiction (see test_prose_checks.py for the calibration
corpus). The limits are engineering heuristics, not research findings and not
an authorship detector. A tripped check produces a revision brief that quotes
the actual sentences and asks the writer to keep the best one and rewrite the
rest.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

# ##################################################################
# patterns
# each regex finds one occurrence of a device in a single sentence.

# "uneven, labored, but steady" / "kitchen, broadcast and lights": three
# short items (one or two words each) where the third closes the clause.
# longer clause series ("he turned, found his coat, and left") are ordinary
# narration and deliberately not counted.
_ITEM = r"[A-Za-z'’-]+(?: [A-Za-z'’-]+)?"
_CLOSE = r"(?=[.,;:!?—\"”]|$)"
_TRIAD_SERIES = re.compile(rf"(?:^|(?<=[,;:—(] )|(?<=—)){_ITEM}, {_ITEM},? (?:and|or|but|then) {_ITEM}{_CLOSE}")
# "frozen, amber, slightly unreal." — three bare items closing a sentence
_TRIAD_BARE = re.compile(rf"(?:^|(?<=[,;:—] )|(?<=—)){_ITEM}, {_ITEM}, {_ITEM}[.!?]$")
# a sentence short enough to be one beat of a staccato run
_BEAT_WORDS = 4

_CONTRAST_PATTERNS = [
    # not X, but Y / not because X but because Y / not just X but Y
    re.compile(r"\bnot (?:just |only |simply |merely |because )?[^.;!?\n]{1,60}?,? but\b", re.IGNORECASE),
    # It wasn't X. It was Y.
    re.compile(
        r"\b(?:it|this|that|he|she|they)(?: wasn't| isn't| was not| is not| weren't| aren't)\b[^.!?\n]{1,60}[.!?;—]+ ?"
        r"(?:it|this|that|he|she|they) (?:was|is|were|are)\b",
        re.IGNORECASE,
    ),
    # less X than Y (as a reframing, not a comparison of quantities)
    re.compile(r"\bless (?:a |an |about )[^.;!?\n]{1,40}? than\b", re.IGNORECASE),
]

# stock phrasing that recurs across model-written fiction. a single use is
# fine; the trigger is the scene total.
STOCK_PHRASES = [
    r"hung in the air",
    r"hangs in the air",
    r"the weight of",
    r"something shifted",
    r"something in (?:him|her|them) shifted",
    r"a beat\b",
    r"let out a breath",
    r"breath (?:she|he|they) didn't know",
    r"jaw tightened",
    r"the silence stretched",
    r"silence settled",
    r"a flicker of",
    r"palpable",
    r"testament to",
    r"tapestry",
    r"\bdelve",
    r"didn't reach (?:his|her|their) eyes",
    r"the ghost of a smile",
    r"for the first time in (?:years|a long time|forever)",
    r"the air (?:thickened|was thick)",
    r"a (?:low )?hum of",
    r"ozone",
    r"something like",
    r"in that moment",
    r"(?:her|his|their) heart (?:hammered|pounded|raced)",
    r"(?:she|he|they) realized",
    r"a wave of",
    r"a surge of",
]
_STOCK_RE = re.compile(r"\b(?:" + "|".join(STOCK_PHRASES) + r")", re.IGNORECASE)

# counselling / self-help register, counted only inside dialogue. fine for a
# therapist character, odd when every character talks this way.
THERAPY_PHRASES = [
    r"i hear you",
    r"(?:that's|that is|your feelings are|it's) valid",
    r"hold(?:ing)? space",
    r"safe space",
    r"boundar(?:y|ies)",
    r"process(?:ing)? (?:this|that|it|what)",
    r"you don't have to carry",
    r"carry this alone",
    r"it's okay (?:to not be|not to be) okay",
    r"i need you to know",
    r"i'm here for you",
    r"(?:healing|grief) journey",
    r"your truth",
    r"i see you",
    r"that must have been (?:so )?hard",
    r"unpack",
    r"toxic",
    r"trauma",
    r"give yourself (?:grace|permission)",
    r"you're allowed to",
    r"what do you need",
    r"how does that make you feel",
]
_THERAPY_RE = re.compile(r"\b(?:" + "|".join(THERAPY_PHRASES) + r")\b", re.IGNORECASE)

# paragraph-final sentences that explain what the paragraph meant
_MORAL_ENDING = re.compile(
    r"(?:\band that was (?:the point|everything|enough|all)\b|\bmaybe that was\b|\bthat was the thing about\b"
    r"|\bfor the first time in\b|\bsome things\b|\bit was enough\b|\band (?:she|he|they) knew\b"
    r"|\bwhich was (?:its own|a kind of)\b|\bin (?:its|their) own way\b"
    r"|\bto \w+ was to \w+|\bthe (?:jagged |ugly |simple |only |real )?truth\b|\bno (?:more )?room for\b"
    r"|\bthere (?:was|were) no more\b|\bwas (?:everything|nothing)\b|\bof all\.$|\bwhat (?:really )?mattered\b)",
    re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?:(?<=[.!?])|(?<=[.!?][\"”’']))\s+(?=[\"“'A-Z])")
_WORD_RE = re.compile(r"[A-Za-z'’]+")
_QUOTED = re.compile(r"[\"“]([^\"”]{2,})[\"”]")


# ##################################################################
# limit
# a review trigger: trips when count > floor AND the per-1000-word rate is
# above per_thousand. the floor stops a short scene tripping on one use.
@dataclass(frozen=True)
class Limit:
    per_thousand: float
    floor: int


# engineering heuristics, set above the rates measured on the human calibration
# passages in test_prose_checks.py, and below the rates in sampled model scenes.
LIMITS: dict[str, Limit] = {
    "triad": Limit(per_thousand=2.5, floor=2),
    "contrast": Limit(per_thousand=1.5, floor=1),
    "em_dash": Limit(per_thousand=12.0, floor=10),
    "stock_phrase": Limit(per_thousand=2.5, floor=2),
    "therapy_dialogue": Limit(per_thousand=1.0, floor=1),
    "moral_ending": Limit(per_thousand=1.0, floor=1),
    "same_opening": Limit(per_thousand=1.5, floor=1),
}

# what the revision brief asks the writer to do about each device
ADVICE = {
    "triad": "lists of three items or three parallel beats. Keep the strongest; give the rest their natural "
    "number of items or a single exact detail.",
    "contrast": '"not X but Y" / "it wasn\'t X, it was Y" framing. Keep practical corrections and real '
    "arguments; where the narrator or a speaker denies a reading nobody offered, say directly what the thing is "
    "or show it through an action.",
    "em_dash": "em dashes. Keep them for speech that is cut off; use commas, full stops or new sentences elsewhere.",
    "stock_phrase": "stock phrasing that could sit in any novel. Replace each with a detail only this POV "
    "character, in this place, would notice.",
    "therapy_dialogue": "counselling or self-help language in dialogue. Unless that register is this character's "
    "own, make them dodge, act, joke, or turn practical instead of explaining their feelings.",
    "moral_ending": "paragraphs that end by explaining what they meant. End on an action, an image, or a "
    "spoken line.",
    "same_opening": "runs of three or more sentences starting with the same word. Recast one so the rhythm moves.",
}


# ##################################################################
# finding
# one device's count, rate and quoted examples for a scene
@dataclass
class Finding:
    kind: str
    count: int
    per_thousand: float
    limit: Limit
    examples: list[str] = field(default_factory=list)

    # ##################################################################
    # over limit
    # both the absolute floor and the normalised rate must be exceeded
    @property
    def over_limit(self) -> bool:
        return self.count > self.limit.floor and self.per_thousand > self.limit.per_thousand

    # ##################################################################
    # allowed count
    # how many uses the scene's length can carry before the trigger trips
    def allowed_count(self, words: int) -> int:
        return max(self.limit.floor, int(self.limit.per_thousand * words / 1000))


# ##################################################################
# prose report
# all findings for one scene plus the word count they were normalised by
@dataclass
class ProseReport:
    words: int
    findings: dict[str, Finding]
    sentence_length_spread: float

    # ##################################################################
    # tripped
    # the findings that crossed their review trigger
    def tripped(self) -> list[Finding]:
        return [f for f in self.findings.values() if f.over_limit]

    # ##################################################################
    # needs revision
    # true when any device crossed its trigger
    @property
    def needs_revision(self) -> bool:
        return bool(self.tripped())

    # ##################################################################
    # excess
    # total uses above the allowed counts; a revision must lower this
    def excess(self) -> int:
        return sum(max(0, f.count - f.allowed_count(self.words)) for f in self.findings.values())

    # ##################################################################
    # summary
    # one line per device for logs: kind=count (rate/1000)
    def summary(self) -> str:
        return ", ".join(
            f"{f.kind}={f.count} ({f.per_thousand:.1f}/1000{' OVER' if f.over_limit else ''})"
            for f in self.findings.values()
        )

    # ##################################################################
    # brief
    # the revision instructions for this scene, quoting real sentences
    def brief(self) -> str:
        sections = [_brief_section(f, self.words) for f in self.tripped()]
        return "\n\n".join(sections)


# ##################################################################
# brief section
# one tripped device: what was counted, how many may stay, the quotes
def _brief_section(finding: Finding, words: int) -> str:
    keep = finding.allowed_count(words)
    quotes = "\n".join(f'  - "{e}"' for e in finding.examples[:8])
    return (
        f"- {finding.count} uses of {ADVICE[finding.kind]} At most {keep} should remain.\n"
        f"  Found in:\n{quotes}"
    )


# ##################################################################
# analyse prose
# count every device in a scene. dialogue_lines, when given, are the spoken
# lines from the tagged output; otherwise quoted spans are used.
def analyse_prose(text: str, dialogue_lines: list[str] | None = None) -> ProseReport:
    words = max(1, len(_WORD_RE.findall(text)))
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    sentences = [s for p in paragraphs for s in split_sentences(p)]
    dialogue = dialogue_lines if dialogue_lines is not None else _QUOTED.findall(text)
    hits = {
        "triad": find_triads(sentences),
        "contrast": find_contrasts(paragraphs),
        "em_dash": _em_dash_hits(sentences),
        "stock_phrase": _regex_hits(_STOCK_RE, sentences),
        "therapy_dialogue": _regex_hits(_THERAPY_RE, dialogue),
        "moral_ending": find_moral_endings(paragraphs),
        "same_opening": find_same_openings(sentences),
    }
    findings = {kind: _finding(kind, examples, words) for kind, examples in hits.items()}
    return ProseReport(words=words, findings=findings, sentence_length_spread=sentence_length_spread(sentences))


# ##################################################################
# finding
# wrap the examples for one device with its count and rate
def _finding(kind: str, examples: list[str], words: int) -> Finding:
    return Finding(
        kind=kind,
        count=len(examples),
        per_thousand=len(examples) * 1000 / words,
        limit=LIMITS[kind],
        examples=examples,
    )


# ##################################################################
# split sentences
# rough sentence split good enough for counting devices
def split_sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(paragraph) if s.strip()]


# ##################################################################
# find triads
# sentences containing a three-item series or ending on three bare items
def find_triads(sentences: list[str]) -> list[str]:
    found = [s for s in sentences if _TRIAD_SERIES.search(s) or _TRIAD_BARE.search(s)]
    return found + _staccato_runs(sentences)


# ##################################################################
# staccato runs
# three consecutive very short sentences ("He ran. He fell. He rose.")
def _staccato_runs(sentences: list[str]) -> list[str]:
    runs = []
    index = 0
    while index + 2 < len(sentences):
        window = sentences[index : index + 3]
        if all(_is_beat(s) for s in window):
            runs.append(" ".join(window))
            index += 3
        else:
            index += 1
    return runs


# ##################################################################
# is beat
# a very short narration sentence with real words (not "R." or speech)
def _is_beat(sentence: str) -> bool:
    words = _WORD_RE.findall(sentence)
    quoted = any(q in sentence for q in "\"“”")
    return 0 < len(words) <= _BEAT_WORDS and not quoted and max(len(w) for w in words) > 2


# ##################################################################
# find contrasts
# "not X but Y" style reframings; searched per paragraph because the
# "It wasn't X. It was Y." form spans two sentences
def find_contrasts(paragraphs: list[str]) -> list[str]:
    found = []
    for paragraph in paragraphs:
        for pattern in _CONTRAST_PATTERNS:
            found += [m.group(0) for m in pattern.finditer(paragraph)]
    return found


# ##################################################################
# em dash hits
# one entry per dash so a sentence with two dashes counts twice
def _em_dash_hits(sentences: list[str]) -> list[str]:
    return [s for s in sentences for _ in range(s.count("—") + s.count(" -- "))]


# ##################################################################
# regex hits
# one entry per match, quoting the containing sentence or line
def _regex_hits(pattern: re.Pattern, texts: list[str]) -> list[str]:
    return [t for t in texts for _ in pattern.finditer(t)]


# ##################################################################
# find moral endings
# narration paragraphs whose final sentence explains what it all meant
def find_moral_endings(paragraphs: list[str]) -> list[str]:
    found = []
    for paragraph in paragraphs:
        if paragraph.startswith(('"', "“")):
            continue
        sentences = split_sentences(paragraph)
        if len(sentences) >= 2 and _MORAL_ENDING.search(sentences[-1]):
            found.append(sentences[-1])
    return found


# ##################################################################
# find same openings
# runs of three or more consecutive narration sentences opening on the same
# word ("She ... She ... She ..."); each run counts once
def find_same_openings(sentences: list[str]) -> list[str]:
    runs = []
    index = 0
    while index < len(sentences):
        end = _run_end(sentences, index)
        if end - index >= 3:
            runs.append(" ".join(sentences[index:end]))
        index = max(end, index + 1)
    return runs


# ##################################################################
# run end
# index just past the run of sentences sharing sentences[start]'s first word
def _run_end(sentences: list[str], start: int) -> int:
    first = _first_word(sentences[start])
    end = start + 1
    while first and end < len(sentences) and _first_word(sentences[end]) == first:
        end += 1
    return end


# ##################################################################
# first word
# lowercased opening word of a narration sentence; dialogue never counts
def _first_word(sentence: str) -> str:
    if sentence.startswith(('"', "“")):
        return ""
    match = _WORD_RE.search(sentence)
    return match.group(0).lower() if match else ""


# ##################################################################
# sentence length spread
# coefficient of variation of sentence lengths; reported for logs only,
# because legitimate styles differ widely here
def sentence_length_spread(sentences: list[str]) -> float:
    lengths = [len(_WORD_RE.findall(s)) for s in sentences]
    lengths = [n for n in lengths if n]
    if len(lengths) < 2:
        return 0.0
    return statistics.pstdev(lengths) / statistics.mean(lengths)
