"""Lightweight structured fact ledger for story continuity.

This is a deliberately CHEAP replacement for the old subject/attribute/value
ledger that was removed (it ran full contradiction-detection AND regenerated the
prose on every contradiction, costing ~2.6x prose calls per section). This
version does exactly ONE cheap `chat_structured` extraction call per section on
the FAST tier and NEVER triggers regeneration — contradictions are only
flagged/returned for a non-blocking log, never acted on.

It complements `retrieval_memory.py`: the retrieval memory holds every sentence
as a fuzzy vector; the ledger holds a small set of hard, high-value canonical
facts (physical descriptions, pets + breeds, relationships, locations, ages,
notable possessions) as an authoritative key/value store the prompt can pin down.

Storage shape (matches the design spec):
    dict[str, dict[str, tuple[str, int]]]
    entity -> { attribute -> (value, section_id_last_set) }

`section_id_last_set` is an integer ordinal (section index in write order) so a
later value overwrites an earlier one and recency is trivially comparable.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from brain import chat_structured


# ##################################################################
# extraction schema — kept intentionally tiny so it is cheap and reliable on the
# FREE_FAST tier. One flat list of {entity, attribute, value} triples.
class ExtractedFact(BaseModel):
    entity: str = Field(description="Canonical name of the character, pet, place or object the fact is about")
    attribute: str = Field(description="Short snake_case attribute name, e.g. 'breed', 'hair_color', 'age', 'occupation', 'home_town', 'relationship_to_clara'")
    value: str = Field(description="The concrete value, kept short, e.g. 'beagle', 'auburn', '34', 'lighthouse keeper'")


class ExtractedFacts(BaseModel):
    facts: list[ExtractedFact] = Field(default_factory=list, description="Only NEW or CHANGED high-value facts established in this text")


_EXTRACTION_SYSTEM = """\
You are a continuity editor for a novel. From the passage you are given, extract
ONLY hard, high-value, easily-verifiable facts that must stay consistent across
the whole book. Focus on:
- physical descriptions of people (hair/eye colour, height, distinctive marks)
- named pets (their name AND species/breed)
- family / relationship ties between named characters
- ages
- home / work locations tied to a named entity
- notable named possessions (a specific car, a locket, a weapon)

Rules:
- Emit a fact ONLY if it is concrete and canonical (would be wrong to contradict later).
- Prefer the given known entities; use their exact canonical names.
- Keep each value to a few words. Use a short snake_case attribute.
- Do NOT emit plot events, feelings, opinions, temporary states, or vague description.
- If nothing qualifies, return an empty list. Fewer, solid facts beat many weak ones."""


# ##################################################################
# normalize helpers
def _norm(s: str) -> str:
    return " ".join(str(s).strip().lower().split())


# find an existing dict key that matches `name` case-insensitively; else return
# `name` unchanged (so the first-seen casing becomes the display form).
def _match_key(d: dict, name: str) -> str:
    target = _norm(name)
    for existing in d:
        if _norm(existing) == target:
            return existing
    return name


# coerce assorted fact shapes (pydantic model / dict) into (entity, attribute, value)
def _as_triple(fact) -> tuple[str, str, str] | None:
    if isinstance(fact, ExtractedFact):
        entity, attribute, value = fact.entity, fact.attribute, fact.value
    elif isinstance(fact, dict):
        entity = fact.get("entity", "")
        attribute = fact.get("attribute", "")
        value = fact.get("value", "")
    else:
        entity = getattr(fact, "entity", "")
        attribute = getattr(fact, "attribute", "")
        value = getattr(fact, "value", "")
    entity = str(entity).strip()
    attribute = str(attribute).strip()
    value = str(value).strip()
    if not entity or not attribute or not value:
        return None
    return entity, attribute, value


# ##################################################################
# fact ledger
# entity -> { attribute -> (value, section_ordinal) }. No merge logic, no
# regeneration: `update` always overwrites with the latest value.
class FactLedger:
    def __init__(self) -> None:
        self._facts: dict[str, dict[str, tuple[str, int]]] = {}

    def __len__(self) -> int:
        return sum(len(attrs) for attrs in self._facts.values())

    def entities(self) -> list[str]:
        return list(self._facts.keys())

    # ##################################################################
    # extract facts
    # ONE cheap structured call. Returns the parsed list of ExtractedFact for the
    # caller to feed straight into `update` and `check_conflicts`.
    def extract_facts(self, text: str, known_entities: list[str]) -> list[ExtractedFact]:
        if not text or not text.strip():
            return []
        roster = ", ".join(e for e in known_entities if e and e.strip()) or "(none provided)"
        user = (
            f"KNOWN ENTITIES (prefer these exact names): {roster}\n\n"
            f"PASSAGE:\n{text}\n\n"
            "Extract only the new or changed high-value canonical facts as {entity, attribute, value} triples."
        )
        messages = [
            {"role": "system", "content": _EXTRACTION_SYSTEM},
            {"role": "user", "content": user},
        ]
        result = chat_structured(messages, ExtractedFacts)
        facts = getattr(result, "facts", None) or []
        # normalize to ExtractedFact instances (chat_structured returns the model,
        # but be defensive about dict-shaped cached payloads).
        out: list[ExtractedFact] = []
        for f in facts:
            triple = _as_triple(f)
            if triple is None:
                continue
            entity, attribute, value = triple
            out.append(ExtractedFact(entity=entity, attribute=_norm(attribute).replace(" ", "_"), value=value))
        return out

    # ##################################################################
    # update
    # write facts into the ledger, section-stamped, always overwriting. No merge,
    # no contradiction handling — that is `check_conflicts`' (advisory) job.
    def update(self, facts, section_id: int) -> None:
        for fact in facts:
            triple = _as_triple(fact)
            if triple is None:
                continue
            entity, attribute, value = triple
            entity_key = _match_key(self._facts, entity)
            attrs = self._facts.setdefault(entity_key, {})
            attr_key = _match_key(attrs, attribute)
            attrs[attr_key] = (value, int(section_id))

    # ##################################################################
    # check conflicts
    # compare newly extracted facts against existing ledger entries for the same
    # (entity, attribute) and return human-readable conflict descriptions. Purely
    # advisory: this NEVER blocks, mutates, or regenerates anything. The
    # integration wave writes the returned strings to a non-blocking log.
    def check_conflicts(self, facts) -> list[str]:
        conflicts: list[str] = []
        for fact in facts:
            triple = _as_triple(fact)
            if triple is None:
                continue
            entity, attribute, value = triple
            entity_key = _match_key(self._facts, entity)
            attrs = self._facts.get(entity_key)
            if not attrs:
                continue
            attr_key = _match_key(attrs, attribute)
            if attr_key not in attrs:
                continue
            old_value, old_section = attrs[attr_key]
            if _norm(old_value) != _norm(value):
                conflicts.append(
                    f"{entity_key} {attribute}: was '{old_value}' (set in section {old_section}), "
                    f"now '{value}'"
                )
        return conflicts

    # ##################################################################
    # get canon facts
    # flatten to {"Entity attribute": value} formatted for craft.render_canon_facts.
    # The most recently set value per (entity, attribute) is authoritative (it is
    # the only value stored — updates overwrite).
    def get_canon_facts(self, entities: list[str]) -> dict[str, str]:
        wanted = {_norm(e) for e in entities if e and e.strip()} if entities else None
        out: dict[str, str] = {}
        for entity, attrs in self._facts.items():
            if wanted is not None and _norm(entity) not in wanted:
                continue
            for attribute, (value, _section) in attrs.items():
                label = f"{entity} {str(attribute).replace('_', ' ')}".strip()
                out[label] = value
        return out

    # ##################################################################
    # rebuild from sections
    # idempotently reconstruct the ledger from already-written sections on resume,
    # mirroring RetrievalMemory.ensure_section: sections are processed in order,
    # each extraction call is cached in brain.py by input hash so a resume re-runs
    # them for free, and later values overwrite earlier ones exactly as a fresh run
    # would. `sections` is an ordered iterable of (section_id_label, text) OR bare
    # text strings; `known_entities` seeds the extraction roster.
    @classmethod
    def rebuild_from_sections(cls, sections, known_entities: list[str] | None = None) -> "FactLedger":
        ledger = cls()
        entities = list(known_entities or [])
        for ordinal, item in enumerate(sections):
            if isinstance(item, (tuple, list)) and len(item) == 2:
                text = item[1]
            else:
                text = item
            if not text or not str(text).strip():
                continue
            facts = ledger.extract_facts(str(text), entities)
            ledger.update(facts, ordinal)
        return ledger

    # ##################################################################
    # persistence — same to_dict/from_dict + save/load surface RetrievalMemory
    # uses, so the pipeline can record() this as its own JSON checkpoint. Tuples
    # serialize as [value, section] lists.
    def to_dict(self) -> dict:
        return {
            entity: {attr: [value, section] for attr, (value, section) in attrs.items()}
            for entity, attrs in self._facts.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FactLedger":
        ledger = cls()
        for entity, attrs in (data or {}).items():
            clean: dict[str, tuple[str, int]] = {}
            for attr, pair in attrs.items():
                value = str(pair[0])
                section = int(pair[1]) if len(pair) > 1 and pair[1] is not None else 0
                clean[attr] = (value, section)
            ledger._facts[entity] = clean
        return ledger

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path) -> "FactLedger":
        if not Path(path).exists():
            return cls()
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_dict(data)
