import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from models import Contradiction, Fact

SUBJECT_FUZZY_THRESHOLD = 0.85
TRIVIAL_NAME_ATTRIBUTES = {"name", "first_name", "last_name", "full_name"}
MAX_VALUE_LENGTH = 80
ATTRIBUTE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _key(subject: str, attribute: str) -> tuple[str, str]:
    return subject.strip().lower(), attribute.strip().lower()


def _norm(s: str) -> str:
    return s.strip().lower()


def _is_trivial_name_fact(fact: Fact) -> bool:
    if fact.attribute.strip().lower() not in TRIVIAL_NAME_ATTRIBUTES:
        return False
    subject_words = {w.lower() for w in fact.subject.split()}
    value_words = {w.lower() for w in fact.value.split()}
    return bool(value_words) and value_words.issubset(subject_words)


def _is_garbage_fact(fact: Fact) -> bool:
    if not fact.subject.strip() or not fact.value.strip() or not fact.attribute.strip():
        return True
    if len(fact.value) > MAX_VALUE_LENGTH:
        return True
    if not ATTRIBUTE_PATTERN.match(fact.attribute.strip().lower()):
        return True
    return False


class FactLedger:
    def __init__(self) -> None:
        self._facts: dict[tuple[str, str], Fact] = {}

    def __len__(self) -> int:
        return len(self._facts)

    def all(self) -> list[Fact]:
        return list(self._facts.values())

    def get(self, subject: str, attribute: str) -> Fact | None:
        canonical = self.canonical_subject(subject) or subject
        return self._facts.get(_key(canonical, attribute))

    def known_subjects(self) -> list[str]:
        seen: dict[str, str] = {}
        for fact in self._facts.values():
            seen.setdefault(_norm(fact.subject), fact.subject)
        return sorted(seen.values())

    def canonical_subject(self, candidate: str) -> str | None:
        cand = _norm(candidate)
        if not cand:
            return None
        subjects = {_norm(f.subject): f.subject for f in self._facts.values()}
        if cand in subjects:
            return subjects[cand]

        cand_words = set(cand.split())
        for norm, original in subjects.items():
            other_words = set(norm.split())
            if cand_words and other_words and cand_words.issubset(other_words):
                return original
            if other_words and cand_words and other_words.issubset(cand_words):
                return original

        best = None
        best_score = 0.0
        for norm, original in subjects.items():
            score = SequenceMatcher(None, cand, norm).ratio()
            if score > best_score:
                best_score = score
                best = original
        if best is not None and best_score >= SUBJECT_FUZZY_THRESHOLD:
            return best
        return None

    def add(self, fact: Fact) -> None:
        canonical = self.canonical_subject(fact.subject)
        if canonical and canonical != fact.subject:
            fact = fact.model_copy(update={"subject": canonical})
        self._facts[_key(fact.subject, fact.attribute)] = fact

    def add_all(self, facts: list[Fact]) -> list[Fact]:
        added = []
        for fact in facts:
            if _is_garbage_fact(fact) or _is_trivial_name_fact(fact):
                continue
            canonical = self.canonical_subject(fact.subject)
            if canonical and canonical != fact.subject:
                fact = fact.model_copy(update={"subject": canonical})
            if _key(fact.subject, fact.attribute) not in self._facts:
                self.add(fact)
                added.append(fact)
        return added

    def find_contradictions(self, candidates: list[Fact]) -> list[Contradiction]:
        result = []
        for cand in candidates:
            if _is_garbage_fact(cand) or _is_trivial_name_fact(cand):
                continue
            existing = self.get(cand.subject, cand.attribute)
            if existing is None:
                continue
            if _norm(existing.value) == _norm(cand.value):
                continue
            result.append(Contradiction(existing=existing, new_value=cand.value, quote=""))
        return result

    def render_for_prompt(self, subjects: list[str] | None = None) -> str:
        if not self._facts:
            return "(no canonical facts established yet)"

        if subjects is None:
            relevant = list(self._facts.values())
        else:
            wanted = {s.strip().lower() for s in subjects}
            relevant = [f for f in self._facts.values() if f.subject.strip().lower() in wanted]
            if not relevant:
                return "(no canonical facts for these subjects yet)"

        by_subject: dict[str, list[Fact]] = {}
        for fact in relevant:
            by_subject.setdefault(fact.subject, []).append(fact)

        lines = []
        for subject in sorted(by_subject.keys()):
            attrs = ", ".join(f"{f.attribute}={f.value}" for f in by_subject[subject])
            lines.append(f"- {subject}: {attrs}")
        return "\n".join(lines)

    def to_json(self) -> list[dict]:
        return [f.model_dump() for f in self._facts.values()]

    @classmethod
    def from_json(cls, data: list[dict]) -> "FactLedger":
        ledger = cls()
        for entry in data:
            ledger.add(Fact(**entry))
        return ledger

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_json(), fh, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Path) -> "FactLedger":
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_json(json.load(fh))
