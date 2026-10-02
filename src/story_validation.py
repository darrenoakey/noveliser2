"""Deterministic validators for generated story plans and prose, plus bounded replanning.

Validators return a list of specific, human-readable deficiencies (empty list = valid).
They are structural: they check that the causal commitments exist, link up and change
state. They deliberately do NOT judge style (no cliche/repetition detectors).

Validation applies only to NEWLY generated plans. Plans restored from old checkpoints
are never re-validated, so they keep their original continuity semantics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Sequence, TypeVar

from models import (
    Chapter, ChapterPlan, Character, CharactersList, ScheduleContract, SectionPlan,
)

MAX_PLAN_ATTEMPTS = 3
MIN_SECTION_WORDS = 600
VALID_SCENE_TYPES = {"scene", "sequel"}


@dataclass(frozen=True)
class PremiseGuard:
    """Caller-supplied invariants a newly generated plan must not violate.

    Required phrases apply to the whole text. Forbidden patterns are (regex, message)
    pairs. When protagonist is set, no other person may be the agent of a real miracle.
    """

    protagonist: str = ""
    required_phrases: tuple[str, ...] = ()
    forbidden: tuple[tuple[str, str], ...] = ()
    allowed_names: tuple[str, ...] = ()


_ROLE_NAME = re.compile(r"\b(Engineer|Lord|Lady|Duke|Captain|Showman)\s+([A-Z][a-z]{2,})\b")


_PRIOR_MIRACLE = re.compile(
    r"\b(partner|brother|sister|mentor|father|mother|husband|wife|someone else|"
    r"another (?:man|woman|person|magician|performer|showman))\b"
    r"[^.?!]{0,90}\b(performed|could perform|could do|did|used|wielded|"
    r"died (?:making|performing))\b"
    r"[^.?!]{0,40}\b(real magic|genuine magic|true magic|actual sorcery|"
    r"the impossible|a bird fly|real impossibility)\b",
    re.IGNORECASE,
)
_NAMED_OTHER_MIRACLE = re.compile(
    r"\b([A-Z][a-z]{2,})\b(?:'s)?\s+(?:once\s+|finally\s+|secretly\s+)?"
    r"(performed|could do|did|used)\s+(?:real magic|genuine magic|true magic)\b"
)

T = TypeVar("T")


class StoryPlanError(ValueError):
    """Raised when a plan or prose still violates the contract after bounded retries."""

    def __init__(self, label: str, issues: Sequence[str], attempts: int):
        self.label = label
        self.issues = list(issues)
        self.attempts = attempts
        super().__init__(f"{label} failed validation after {attempts} attempt(s):\n- " + "\n- ".join(self.issues))


# ##################################################################
# helpers
def _blank(value: str | None) -> bool:
    return not (value or "").strip()


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", (value or "").lower())).strip()


def _id(value: str) -> str:
    return _norm(value.split(":", 1)[0]).replace(" ", "")


def _names(characters: Sequence[Character]) -> set[str]:
    return {_norm(c.name) for c in characters if not _blank(c.name)}


def _pov_names(characters: Sequence[Character]) -> set[str]:
    names = _names(characters)
    first = [_norm(c.name.split()[0]) for c in characters if not _blank(c.name)]
    return names | {name for name in first if first.count(name) == 1}


def _require(issues: list[str], where: str, **fields: str | None) -> None:
    missing = [name for name, value in fields.items() if _blank(value)]
    if missing:
        issues.append(f"{where}: missing {', '.join(missing)}")


def _check_pov(issues: list[str], where: str, pov: str, names: set[str]) -> None:
    if _blank(pov):
        issues.append(f"{where}: missing pov_character")
    elif _norm(pov) not in names:
        issues.append(f"{where}: pov_character '{pov}' is not a character in the cast")


def _check_state_change(issues: list[str], where: str, before: str, after: str) -> None:
    if not _blank(before) and not _blank(after) and _norm(before) == _norm(after):
        issues.append(f"{where}: value_after is identical to value_before; the end state must change")


# ##################################################################
# characters
def validate_characters(cast: CharactersList) -> list[str]:
    issues: list[str] = []
    characters = cast.characters
    names = _names(characters)
    if not any(c.role.value == "protagonist" for c in characters):
        issues.append("cast: no protagonist")
    if len(names) != len(characters):
        issues.append("cast: duplicate or blank character names")
    for c in characters:
        major = c.role.value in ("protagonist", "antagonist")
        if major:
            _require(issues, f"character '{c.name}'", wound=c.wound, lie=c.lie, want=c.want, need=c.need,
                     arc=c.arc, flaw=c.flaw, voice=c.voice, arc_pressure=c.arc_pressure)
            if not c.relationships:
                issues.append(f"character '{c.name}': a {c.role.value} needs at least one relationship")
        elif c.role.value == "supporting":
            _require(issues, f"character '{c.name}'", want=c.want, voice=c.voice)
        for r in c.relationships:
            if _norm(r.other) not in names:
                issues.append(f"character '{c.name}': relationship names '{r.other}', who is not in the cast")
            elif _norm(r.other) == _norm(c.name):
                issues.append(f"character '{c.name}': relationship with themself")
            if _blank(r.dynamic):
                issues.append(f"character '{c.name}': relationship with '{r.other}' has no dynamic")
    return issues


# ##################################################################
# chapters
def validate_chapter_plan(plan: ChapterPlan, characters: Sequence[Character], num_chapters: int,
                          verify_ids_in_events: bool = True) -> list[str]:
    issues: list[str] = []
    chapters = plan.chapters
    if len(chapters) != num_chapters:
        issues.append(f"expected exactly {num_chapters} chapters, got {len(chapters)}")
    names = _pov_names(characters)
    if _blank(plan.central_question):
        issues.append("plan: missing central_question")

    planted: dict[str, int] = {}   # setup id -> chapter index where first planted
    paid: dict[str, int] = {}
    for i, ch in enumerate(chapters):
        where = f"chapter {i + 1}"
        is_first, is_last = i == 0, i == len(chapters) - 1
        _require(issues, where, title=ch.title, opening_situation=ch.opening_situation,
                 closing_situation=ch.closing_situation, pursuit=ch.pursuit, opposition=ch.opposition,
                 stakes=ch.stakes, choice=ch.choice, cost=ch.cost, reversal=ch.reversal,
                 value_before=ch.value_before, value_after=ch.value_after)
        if not ch.key_events:
            issues.append(f"{where}: missing key_events")
        _check_pov(issues, where, ch.pov_character, names)
        if not is_first and _blank(ch.cause_from_previous):
            issues.append(f"{where}: missing cause_from_previous (what in chapter {i} forces this chapter)")
        if not is_last and _blank(ch.open_question):
            issues.append(f"{where}: missing open_question (why the reader turns the page)")
        _check_state_change(issues, where, ch.value_before, ch.value_after)
        event_text = _norm(" ".join(ch.key_events)).replace(" ", "")
        for pid in ch.payoffs:
            key = _id(pid)
            if key not in planted:
                issues.append(f"{where}: payoff '{pid}' has no earlier setup")
            else:
                if key in paid:
                    issues.append(f"{where}: payoff '{pid}' repeats chapter {paid[key]}; plant once and pay once")
                else:
                    paid[key] = i + 1
            if verify_ids_in_events and key not in event_text:
                issues.append(f"{where}: payoff '{pid}' is absent from key_events; dramatize it there")
        for sid in ch.setups:
            key = _id(sid)
            if key in planted:
                issues.append(f"{where}: setup '{sid}' was already planted in chapter {planted[key] + 1}; plant it once")
            else:
                planted[key] = i
            if verify_ids_in_events and key not in event_text:
                issues.append(f"{where}: setup '{sid}' is absent from key_events; plant it visibly there")
    if len(chapters) > 1 and not any(idx < len(chapters) - 1 for idx in planted.values()):
        issues.append("plan: plant at least one salient setup early and pay it off in a later chapter")
    for sid, idx in planted.items():
        if sid not in paid and idx < len(chapters) - 1:
            issues.append(f"chapter {idx + 1}: setup '{sid}' is never paid off in a later chapter")

    threads = {_norm(s) for s in plan.subplots}
    advanced = {_norm(ch.subplot) for ch in chapters if not _blank(ch.subplot)}
    for thread in plan.subplots:
        if _norm(thread) not in advanced:
            issues.append(f"plan: subplot '{thread}' is never advanced by any chapter")
    for ch in chapters:
        if not _blank(ch.subplot):
            if threads and _norm(ch.subplot) not in threads:
                issues.append(f"chapter {ch.number}: subplot '{ch.subplot}' is not declared in plan.subplots")
            if _blank(ch.subplot_change):
                issues.append(f"chapter {ch.number}: subplot '{ch.subplot}' has no subplot_change")
    return issues


# ##################################################################
# schedule contract
def _contains_anchor(text: str, anchor: str) -> bool:
    """Return whether a model-authored anchor occurs verbatim modulo spacing/punctuation."""
    normalized_anchor = _norm(anchor).replace(" ", "")
    normalized_text = _norm(text).replace(" ", "")
    return bool(normalized_anchor) and normalized_anchor in normalized_text


def _quote_anchor(anchor: str) -> str:
    return anchor.replace("\n", " ").strip()


# ##################################################################
# premise
def validate_unique_miracle(text: str, protagonist: str) -> list[str]:
    """Reject text that gives a real supernatural feat to anyone but the protagonist."""
    if _blank(protagonist):
        return []
    issues: list[str] = []
    for match in _PRIOR_MIRACLE.finditer(text):
        issues.append(
            f"premise: real magic is attributed to someone other than {protagonist}: "
            f"'{match.group(0)}'"
        )
    for match in _NAMED_OTHER_MIRACLE.finditer(text):
        name = match.group(1)
        if name.lower() == protagonist.lower() or name.lower() in {"the", "his", "her"}:
            continue
        issues.append(
            f"premise: '{name}' performs real magic; only {protagonist} may do so: "
            f"'{match.group(0)}'"
        )
    return issues


def validate_premise(text: str, guard: PremiseGuard | None, *,
                     require_phrases: bool = True) -> list[str]:
    """Return premise violations. Empty guard means no extra invariant."""
    if guard is None:
        return []
    issues: list[str] = []
    if require_phrases:
        normalized = _norm(text)
        for phrase in guard.required_phrases:
            if _norm(phrase) not in normalized:
                issues.append(f"premise: missing required material '{phrase}'")
    for pattern, message in guard.forbidden:
        if re.search(pattern, text, flags=re.IGNORECASE):
            issues.append(f"premise: {message}")
    issues.extend(validate_unique_miracle(text, guard.protagonist))
    if guard.allowed_names:
        allowed = {name.lower() for name in guard.allowed_names}
        for match in _ROLE_NAME.finditer(text):
            if match.group(2).lower() not in allowed:
                issues.append(
                    f"premise: invented named person '{match.group(0)}'; "
                    "use an existing cast member or an unnamed role"
                )
    return issues


def declare_used_subplots(plan: ChapterPlan) -> ChapterPlan:
    """Project short subplot ids the chapters already use into the plan list.

    The model often advances a thread in a chapter and forgets to copy that id into
    plan.subplots. That is bookkeeping, not a new story beat.
    """
    declared = {_norm(name) for name in plan.subplots}
    for chapter in plan.chapters:
        label = (chapter.subplot or "").strip()
        if label and re.fullmatch(r"[A-Za-z][A-Za-z0-9-]{0,31}", label) and _norm(label) not in declared:
            plan.subplots.append(label)
            declared.add(_norm(label))
    return plan


def plan_narrative_text(plan: ChapterPlan) -> str:
    """Join the narrative fields a premise check must see, excluding machine IDs."""
    parts = [plan.central_question, *plan.subplots]
    for chapter in plan.chapters:
        parts.extend([
            chapter.title, chapter.opening_situation, chapter.chapter_goal,
            chapter.closing_situation, *chapter.key_events, chapter.cause_from_previous,
            chapter.pursuit, chapter.opposition, chapter.stakes, chapter.choice,
            chapter.cost, chapter.reversal, chapter.value_before, chapter.value_after,
            chapter.subplot_change, chapter.open_question,
        ])
    return "\n".join(part for part in parts if part)


def validate_schedule_contract(schedule: ScheduleContract, num_chapters: int) -> list[str]:
    """Validate bookkeeping only; semantic identity remains the model's commitment."""
    issues: list[str] = []
    if num_chapters < 1:
        issues.append("schedule: num_chapters must be at least 1")
    if not 1 <= len(schedule.obligations) <= 3:
        issues.append("schedule: requires between 1 and 3 obligations")

    seen_ids: set[str] = set()
    for obligation in schedule.obligations:
        if obligation.id in seen_ids:
            issues.append(f"schedule: duplicate obligation id '{obligation.id}'")
        seen_ids.add(obligation.id)
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,47}", obligation.id):
            issues.append(f"schedule obligation '{obligation.id}': id must be a stable lowercase hyphenated identifier")
        if not 1 <= obligation.plant_chapter < obligation.payoff_chapter <= num_chapters:
            issues.append(
                f"schedule obligation '{obligation.id}': plant_chapter {obligation.plant_chapter} and "
                f"payoff_chapter {obligation.payoff_chapter} must be strictly increasing and within "
                f"1..{num_chapters}. There is no chapter {num_chapters + 1}; move the later event into "
                f"chapter {num_chapters} and delete any handoff past that chapter."
            )
        if _norm(obligation.plant_anchor) == _norm(obligation.payoff_anchor):
            issues.append(f"schedule obligation '{obligation.id}': plant_anchor and payoff_anchor must describe distinct events")

    expected = {(chapter, chapter + 1) for chapter in range(1, num_chapters)}
    actual = {(handoff.from_chapter, handoff.to_chapter) for handoff in schedule.handoffs}
    if actual != expected:
        issues.append(
            "schedule: requires exactly one adjacent handoff for every chapter boundary; "
            f"expected {sorted(expected)}, got {sorted(actual)}. "
            f"Do not include a handoff to chapter {num_chapters + 1}."
        )
    if len(actual) != len(schedule.handoffs):
        issues.append("schedule: duplicate chapter handoff")
    return issues


def apply_schedule(plan: ChapterPlan, schedule: ScheduleContract) -> ChapterPlan:
    """Project contract IDs onto a plan without creating or changing narrative content."""
    setups_by_chapter: dict[int, list[str]] = {}
    payoffs_by_chapter: dict[int, list[str]] = {}
    for obligation in schedule.obligations:
        setups_by_chapter.setdefault(obligation.plant_chapter, []).append(obligation.id)
        payoffs_by_chapter.setdefault(obligation.payoff_chapter, []).append(obligation.id)
    for chapter in plan.chapters:
        chapter.setups = setups_by_chapter.get(chapter.number, [])
        chapter.payoffs = payoffs_by_chapter.get(chapter.number, [])
    return plan


def validate_plan_against_schedule(plan: ChapterPlan, schedule: ScheduleContract) -> list[str]:
    """Require model-authored evidence for every frozen contract anchor and handoff."""
    issues: list[str] = []
    chapters_by_number: dict[int, Chapter] = {}
    duplicate_numbers: set[int] = set()
    for chapter in plan.chapters:
        if chapter.number in chapters_by_number:
            duplicate_numbers.add(chapter.number)
        chapters_by_number[chapter.number] = chapter
    for number in sorted(duplicate_numbers):
        issues.append(f"plan: duplicate chapter number {number}")

    expected_setups: dict[int, list[str]] = {}
    expected_payoffs: dict[int, list[str]] = {}
    for obligation in schedule.obligations:
        expected_setups.setdefault(obligation.plant_chapter, []).append(obligation.id)
        expected_payoffs.setdefault(obligation.payoff_chapter, []).append(obligation.id)
        plant = chapters_by_number.get(obligation.plant_chapter)
        payoff = chapters_by_number.get(obligation.payoff_chapter)
        if plant is None:
            issues.append(f"schedule obligation '{obligation.id}': plant chapter {obligation.plant_chapter} is absent from plan")
        elif not _contains_anchor(" ".join(plant.key_events), obligation.plant_anchor):
            issues.append(
                f"chapter {plant.number}: missing scheduled plant evidence for '{obligation.id}'. "
                "Paste this sentence unchanged as its own key_events item: "
                f"{_quote_anchor(obligation.plant_anchor)}"
            )
        if payoff is None:
            issues.append(f"schedule obligation '{obligation.id}': payoff chapter {obligation.payoff_chapter} is absent from plan")
        elif not _contains_anchor(" ".join(payoff.key_events), obligation.payoff_anchor):
            issues.append(
                f"chapter {payoff.number}: missing scheduled payoff evidence for '{obligation.id}'. "
                "Paste this sentence unchanged as its own key_events item: "
                f"{_quote_anchor(obligation.payoff_anchor)}"
            )

    for chapter in plan.chapters:
        if chapter.setups != expected_setups.get(chapter.number, []):
            issues.append(f"chapter {chapter.number}: setups do not match the schedule contract")
        if chapter.payoffs != expected_payoffs.get(chapter.number, []):
            issues.append(f"chapter {chapter.number}: payoffs do not match the schedule contract")

    for handoff in schedule.handoffs:
        downstream = chapters_by_number.get(handoff.to_chapter)
        if downstream is None:
            issues.append(f"schedule handoff {handoff.from_chapter}->{handoff.to_chapter}: destination chapter is absent from plan")
        elif not _contains_anchor(downstream.cause_from_previous, handoff.consequence_anchor):
            issues.append(
                f"chapter {downstream.number}: cause_from_previous omits scheduled handoff "
                f"from chapter {handoff.from_chapter}. Paste this sentence unchanged into "
                f"cause_from_previous: {_quote_anchor(handoff.consequence_anchor)}"
            )
    return issues


# ##################################################################
# sections
def validate_section_plan(plan: SectionPlan, chapter: Chapter, characters: Sequence[Character],
                          sections_per_chapter: int, prior_setups: Sequence[str] = ()) -> list[str]:
    """prior_setups: setup ids planted in EARLIER chapters (payable here)."""
    issues: list[str] = []
    sections = plan.sections
    if len(sections) != sections_per_chapter:
        issues.append(f"expected exactly {sections_per_chapter} sections, got {len(sections)}")
    names = _pov_names(characters)
    planted = {_id(s) for s in prior_setups}
    for i, sec in enumerate(sections):
        where = f"chapter {chapter.number} section {i + 1}"
        is_first, is_last = i == 0, i == len(sections) - 1
        _require(issues, where, goal=sec.goal, key_events=sec.key_events, obstacle=sec.obstacle,
                 choice=sec.choice, cost=sec.cost, disaster=sec.disaster,
                 value_before=sec.value_before, value_after=sec.value_after)
        _check_pov(issues, where, sec.pov_character, names)
        if (sec.scene_type or "").strip().lower() not in VALID_SCENE_TYPES:
            issues.append(f"{where}: scene_type must be 'scene' or 'sequel', got '{sec.scene_type}'")
        if not is_first and _blank(sec.cause):
            issues.append(f"{where}: missing cause (what in section {i} forces this one)")
        if not is_last and _blank(sec.next_obligation):
            issues.append(f"{where}: missing next_obligation")
        _check_state_change(issues, where, sec.value_before, sec.value_after)
        for pid in sec.payoffs:
            if _id(pid) not in planted:
                issues.append(f"{where}: payoff '{pid}' has no earlier setup")
        planted.update(_id(s) for s in sec.setups)
    return issues


# ##################################################################
# prose
_META_PATTERNS = [
    r"^\s*(here(?:'s| is)|sure[,!]|certainly|okay[,!]|of course)\b",
    r"\bas an ai\b",
    r"\bword count\b",
    r"^\s*\(?\s*(note|author'?s note|section \d+|chapter \d+)\b",
    r"^\s*#{1,6}\s",
    r"\*\*(section|chapter)\b",
    r"\bi hope this\b",
    r"\bdo you want me to\b",
]


def validate_prose(text: str, min_words: int = MIN_SECTION_WORDS) -> list[str]:
    issues: list[str] = []
    words = len(text.split())
    if words < min_words:
        issues.append(f"prose is only {words} words; write at least {min_words} words of substantive scene")
    for pattern in _META_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            issues.append("prose contains meta-text/commentary/headers instead of pure narrative "
                          f"(matched /{pattern}/); output only story text")
            break
    return issues


# ##################################################################
# bounded replanning
def format_feedback(issues: Sequence[str]) -> str:
    return ("Your previous attempt was REJECTED by deterministic validation. Fix exactly these "
            "deficiencies and keep everything else that was sound:\n- " + "\n- ".join(issues))


def with_feedback(messages: list[dict[str, str]], issues: Sequence[str],
                  prior_draft: str = "") -> list[dict[str, str]]:
    """Give the model its exact rejected draft plus actionable deficiencies."""
    if not issues:
        return messages
    draft = [{"role": "assistant", "content": prior_draft}] if prior_draft else []
    return messages + draft + [{"role": "user", "content": format_feedback(issues)}]


def plan_with_feedback(build: Callable[[list[str]], T], validate: Callable[[T], list[str]],
                       label: str, max_attempts: int = MAX_PLAN_ATTEMPTS) -> T:
    """Call build(issues_from_last_attempt), validate, retry at most max_attempts times.

    Raises StoryPlanError rather than ever returning an invalid result. An exception
    raised by build (e.g. wrong count) counts as a deficiency and is fed back too.
    """
    issues: list[str] = []
    for attempt in range(1, max_attempts + 1):
        try:
            result = build(issues)
        except StoryPlanError:
            raise
        except ValueError as e:
            issues = [f"generation error: {e}"]
            continue
        issues = validate(result)
        if not issues:
            return result
    raise StoryPlanError(label, issues, max_attempts)


def collect_setups(chapters: Sequence[Chapter], before_number: int) -> list[str]:
    """Setup ids planted by chapters strictly before before_number."""
    return [s for ch in chapters if ch.number < before_number for s in ch.setups]
