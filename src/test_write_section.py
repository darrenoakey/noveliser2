"""Real tests for the write_section integration layer. These exercise the pure,
model-free decision logic (near-duplicate guard, retrieval-query broadening,
repetition guard, drift detection, recap, think-tag stripping, canon/fact
plumbing) and the backward-compatible checkpoint loading. No mocks — the only
backend-touching path (actual prose generation) is deliberately factored out of
these functions so the guards are testable without a model call."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from models import Character, CharacterRole, Fact, Section, SectionResult, WritingStyle  # noqa: E402
import write_section as ws  # noqa: E402


def _char(name, bio="a person", traits=None, **kw):
    return Character(name=name, biography=bio, role=CharacterRole.PROTAGONIST,
                     traits=traits or [], **kw)


# ##################################################################
# #16 — near-duplicate guard is a testable pure decision
def test_is_near_duplicate_flags_similar_text():
    a = "The rain fell hard on the tin roof as Mara counted the coins one by one."
    # near-identical (one word changed) -> should be flagged
    b = "The rain fell hard on the tin roof as Mara counted the coins two by two."
    assert ws.is_near_duplicate(a, b, threshold=0.6)


def test_is_near_duplicate_ignores_distinct_text():
    a = "The rain fell hard on the tin roof as Mara counted the coins one by one."
    b = "Sunlight blazed over the desert highway while Jack argued with the mechanic about brakes."
    assert not ws.is_near_duplicate(a, b, threshold=0.6)


def test_is_near_duplicate_empty_is_false():
    assert not ws.is_near_duplicate("", "something")
    assert not ws.is_near_duplicate("something", "")


def test_similarity_bounds():
    assert ws._similarity("same words here", "same words here") == 1.0
    assert ws._similarity("", "") == 1.0
    assert ws._similarity("abc def", "") == 0.0


# ##################################################################
# #11 — retrieval query broadening pulls entities from character sheets
def test_extract_scene_entities_finds_named_pet():
    c = _char("Elara", bio="Elara lives in Blackreach with her beagle named Rex.")
    ents = ws.extract_scene_entities([c])
    assert "Rex" in ents
    assert "Blackreach" in ents
    # the character's own name is excluded
    assert "Elara" not in ents


def test_build_retrieval_query_includes_entities_and_events():
    c = _char("Elara", bio="Elara walks her dog Rex by the Grey Harbor each dawn.")
    s = Section(number=1, goal="Reach the harbor", key_events="Elara loses Rex in the fog")
    q = ws.build_retrieval_query(s, [c])
    assert "Reach the harbor" in q
    assert "Elara loses Rex" in q
    assert "Rex" in q
    assert "Harbor" in q


# ##################################################################
# #38 — repetition guard against the manuscript so far
def test_overused_ngrams_flags_repeated_phrase():
    manuscript = ("the weight of the world " * 6)
    section = "she felt the weight of the world again"
    flagged = ws.overused_ngrams(section, manuscript, threshold=5, n=3)
    assert any("weight of the" in g for g in flagged)


def test_overused_ngrams_empty_manuscript():
    assert ws.overused_ngrams("some new text here", "", threshold=5) == []


# ##################################################################
# #65 — prior-section-ending recap
def test_last_sentences_returns_tail():
    text = "First sentence here. Second sentence follows. Third and final sentence lands."
    out = ws.last_sentences(text, 2)
    assert "Third and final sentence lands." in out
    assert "First sentence here." not in out


def test_last_sentences_empty():
    assert ws.last_sentences("", 3) == ""


# ##################################################################
# #30 — plan-vs-prose drift detection
def test_find_dropped_beats_flags_missing_beat():
    s = Section(
        number=1, goal="g",
        key_events="Mara defuses the harbor bomb; Jack betrays the smugglers at the warehouse",
    )
    prose = "Mara knelt by the harbor bomb and cut the wire. The device went silent."
    dropped = ws.find_dropped_beats(s, prose)
    # the warehouse-betrayal beat is absent from the prose
    assert any("betray" in d.lower() or "warehouse" in d.lower() for d in dropped)


def test_find_dropped_beats_none_when_present():
    s = Section(number=1, goal="g", key_events="Mara defuses the harbor bomb")
    prose = "Mara defuses the harbor bomb with steady hands while the crowd scatters."
    assert ws.find_dropped_beats(s, prose) == []


# ##################################################################
# think-tag / reasoning-preamble stripping for PROSE_TIER (reasoning mode)
def test_strip_think_removes_block():
    raw = "<think>Let me plan the scene and the beats.</think>\nThe door opened."
    assert ws._strip_think(raw) == "The door opened."


def test_strip_think_dangling_close_tag():
    raw = "I should open on the storm and keep it tense.</think>\nRain lashed the window."
    assert ws._strip_think(raw) == "Rain lashed the window."


def test_strip_think_passthrough_plain_prose():
    raw = "The house was quiet.\nToo quiet."
    assert ws._strip_think(raw) == raw.strip()


def test_postprocess_strips_meta_and_think():
    raw = "<think>plan</think>\nHere's the section:\nThe morning was cold."
    out = ws._postprocess(raw)
    assert "plan" not in out
    assert out.strip().startswith("The morning was cold.")


# ##################################################################
# #2/#27 — canon block plumbing against a duck-typed ledger
class _StubLedger:
    def __init__(self, facts):
        self._facts = facts
        self.updates = []

    def get_canon_facts(self, entities):
        return {k: v for k, v in self._facts.items()}

    def extract_facts(self, text, known_entities):
        return [{"subject": "Rex", "attribute": "breed", "value": "beagle"}]

    def update(self, facts, section_id):
        self.updates.append((facts, section_id))


def test_render_canon_block_uses_ledger():
    ledger = _StubLedger({"Rex_breed": "beagle"})
    block = ws._render_canon_block(ledger, ["Elara"], ["Rex"])
    assert "CANON FACTS" in block
    assert "Rex_breed: beagle" in block


def test_render_canon_block_none_ledger():
    assert ws._render_canon_block(None, ["Elara"], ["Rex"]) == ""


def test_extract_facts_coerces_dicts_to_facts():
    ledger = _StubLedger({})
    facts = ws._extract_facts(ledger, "Rex is a beagle.", ["Rex"], "ch1.s1")
    assert len(facts) == 1
    assert isinstance(facts[0], Fact)
    assert facts[0].value == "beagle"
    assert facts[0].first_seen == "ch1.s1"


def test_extract_facts_none_ledger_is_empty():
    assert ws._extract_facts(None, "text", ["Rex"], "ch1.s1") == []


# ##################################################################
# integration against the REAL fact_ledger types (no backend: we hand it
# ExtractedFact objects directly rather than making the extraction call).
def test_extract_facts_converts_real_extractedfact_to_fact():
    from fact_ledger import ExtractedFact

    class _RealShapeLedger:
        def extract_facts(self, text, known_entities):
            # fact_ledger uses `entity`, not `subject`
            return [ExtractedFact(entity="Rex", attribute="breed", value="beagle")]

    facts = ws._extract_facts(_RealShapeLedger(), "Rex is a beagle.", ["Rex"], "ch1.s1")
    assert len(facts) == 1
    assert facts[0].subject == "Rex"  # entity -> subject
    assert facts[0].value == "beagle"
    assert facts[0].first_seen == "ch1.s1"


def test_pipeline_update_ledger_feeds_real_ledger():
    # the Fact -> {entity,...} translation in pipeline._update_ledger must make
    # facts actually land in a real FactLedger and surface as canon facts.
    import pipeline
    from fact_ledger import FactLedger
    from models import Fact as _Fact

    ledger = FactLedger()
    facts = [_Fact(subject="Rex", attribute="breed", value="beagle", first_seen="ch1.s1")]
    pipeline._update_ledger(ledger, tmp_ledger_path(), facts, 0)
    canon = ledger.get_canon_facts(["Rex"])
    assert any("beagle" == v for v in canon.values())


def tmp_ledger_path():
    import tempfile
    return Path(tempfile.mkdtemp()) / "fact_ledger.json"


# ##################################################################
# #30 — continuity warnings log is non-blocking and idempotent per section
def test_continuity_warnings_written_and_replaced(tmp_path):
    ws._log_continuity_warnings(tmp_path, "ch1.s1", "dup warning", ["the weight of the"], ["a beat"])
    path = tmp_path / ws.CONTINUITY_WARNINGS_FILE
    data = json.loads(path.read_text())
    assert len(data) == 1
    assert data[0]["section"] == "ch1.s1"
    assert data[0]["near_duplicate"] == "dup warning"
    # re-logging the same section replaces, does not duplicate
    ws._log_continuity_warnings(tmp_path, "ch1.s1", None, ["other phrase here"], [])
    data = json.loads(path.read_text())
    assert len(data) == 1
    assert data[0]["overused_phrases"] == ["other phrase here"]


def test_continuity_warnings_noop_without_signals(tmp_path):
    ws._log_continuity_warnings(tmp_path, "ch1.s1", None, [], [])
    assert not (tmp_path / ws.CONTINUITY_WARNINGS_FILE).exists()


def test_continuity_warnings_noop_without_dir():
    # must not raise when novel_dir is None
    ws._log_continuity_warnings(None, "ch1.s1", "dup", [], [])


# ##################################################################
# #76 — SectionResult.new_facts round-trips through the checkpoint
def test_section_result_new_facts_roundtrip():
    sr = SectionResult(text="prose", new_facts=[Fact(subject="Rex", attribute="breed", value="beagle")])
    dumped = sr.model_dump()
    restored = SectionResult(**dumped)
    assert restored.new_facts[0].value == "beagle"


# ##################################################################
# #83 — OLD-shape checkpoints (no new_facts, no ledger/summary data) still load
def test_old_shape_section_checkpoint_loads():
    # an old checkpoint predates new_facts entirely
    old: dict[str, Any] = {"text": "some earlier prose"}
    sr = SectionResult(**old)
    assert sr.text == "some earlier prose"
    assert sr.new_facts == []


def test_old_shape_writing_style_and_section_load():
    # old WritingStyle without pov/tense
    old_ws = {"style_description": "s", "tone": "t", "voice": "v", "pacing": "p", "examples": []}
    style = WritingStyle(**old_ws)
    assert style.pov == "" and style.tense == ""
    # old Section without scene_type/disaster/intensity
    old_sec = {"number": 1, "goal": "g", "key_events": "e"}
    sec = Section(**old_sec)
    assert sec.intensity == "medium"
    # word target still resolves for an old-shape section
    lo, hi = __import__("craft").word_target_for_scene(sec)
    assert lo < hi


# ##################################################################
# #91 — reasoning-tier model emits planning notes instead of prose, with no
# <think> wrapper for _strip_think to catch. Fixtures below are the actual
# heads of two corrupted sections captured from a real generation run
# (chapter_2_section_2.json / chapter_2_section_3.json in a test novel),
# not a synthetic reconstruction.
_REAL_META_COMMENTARY_HEAD_1 = (
    "1.  **Analyze User Input:**\n   - **POV/Tense:** Third-person limited, past tense, "
    "deeply embedded in Mara's consciousness.\n   - **Style:** Smooth, flowing literary "
    "prose, fluid syntax, rich sensory subjectivity, layered subtext. Varied sentence "
    "length, no fragmentation as a mannerism.\n   - **Structure/Goal:** Chapter 2, "
    "Section 2. Processing emotional mirroring of Elias's grief."
)
_REAL_META_COMMENTARY_HEAD_2 = (
    "1.  **Analyze User Input:**\n   - **Role/Task:** Novelist writing prose fiction. "
    "Output ONLY narrative text.\n   - **Style:** Smooth, flowing literary prose.\n   - "
    "**Chapter/Section:** Chapter 2, Section 3. Goal: Mediate with council to stop "
    "demolition.\n   - **Dramatic Shape:** Scene (proactive)."
)
_REAL_PROSE_HEAD = (
    "Mara Voss stood behind the triple-paned glass of her bay window, where the light "
    "fell short and the air remained still enough to suspend dust motes for hours, "
    "maintaining a ledger of Oakhaven Park's deterioration that existed only within the "
    "synaptic pathways of her memory. She had spent decades cataloging the decay of "
    "others' stories in the library stacks; now, at sixty-four, she applied the same "
    "meticulous rigor to the landscape visible from her kitchen sink."
)


def test_looks_like_meta_commentary_flags_real_captured_failures():
    assert ws._looks_like_meta_commentary(_REAL_META_COMMENTARY_HEAD_1) is True
    assert ws._looks_like_meta_commentary(_REAL_META_COMMENTARY_HEAD_2) is True


def test_looks_like_meta_commentary_false_for_real_prose():
    assert ws._looks_like_meta_commentary(_REAL_PROSE_HEAD) is False


def test_looks_like_meta_commentary_false_for_empty():
    assert ws._looks_like_meta_commentary("") is False


def test_looks_like_meta_commentary_false_for_incidental_numbered_sentence():
    # prose that happens to open with a number should not false-positive —
    # only a numbered *bold markdown header* or an explicit label marker does.
    text = "1,200 people showed up to the vigil, more than anyone expected."
    assert ws._looks_like_meta_commentary(text) is False


# ##################################################################
# #93 — truncated response (reasoning budget crowds out the visible answer).
# fixture below is the actual full text of a corrupted section captured from
# a real generation run (chapter_2_section_3.json in a test novel), which
# stopped mid-sentence at 94 words against a 1500-word target floor.
_REAL_TRUNCATED_SECTION = (
    "Mara’s declaration hung in the turpentine-scented air, a quiet promise that "
    "felt both fragile and irrevocable. Elias did not answer immediately. He watched "
    "her from beneath the heavy brow of a man who had spent years learning how to "
    "make himself invisible, his posture rigid against the drafting table as though "
    "bracing for an impact he could not outrun. The silence stretched, filled only "
    "by the rhythmic tap of a dripping faucet and the soft scrape of Biscuit’s "
    "claws on cracked concrete. When Elias finally spoke, his voice carried that "
    "crisp, academic precision she'"
)


def test_looks_truncated_flags_real_captured_failure():
    assert ws._looks_truncated(_REAL_TRUNCATED_SECTION, word_lo=1500) is True


def test_looks_truncated_false_for_real_prose_at_target_length():
    full_length_prose = (_REAL_PROSE_HEAD + " ") * 20  # well over any word floor
    assert ws._looks_truncated(full_length_prose, word_lo=1100) is False


def test_looks_truncated_false_for_legitimately_short_fast_scene():
    # a real "fast" scene's floor is 1100 words (craft.word_target_for_scene) —
    # text right at half that floor, ending cleanly, must not false-positive.
    text = " ".join(["word"] * 550) + " done."
    assert ws._looks_truncated(text, word_lo=1100) is False


def test_looks_truncated_true_for_empty():
    assert ws._looks_truncated("", word_lo=1100) is True


# fixture below is the actual tail of a second corrupted section captured
# from a real generation run (chapter_2_section_3.json in a later test-novel
# run) — 1667 words, well over the target floor, but the very last sentence
# stops mid-clause on a bare comma instead of finishing.
_REAL_TAIL_TRUNCATED_ENDING = (
    "...the demolition crew's voices rose beyond the fence, the mechanical whine "
    "of generators spooling up for the morning. The sky above the marsh lightened "
    "to a thin,"
)


def test_looks_truncated_flags_real_captured_tail_truncation_despite_good_length():
    long_but_cut_off = (_REAL_PROSE_HEAD + " ") * 20 + _REAL_TAIL_TRUNCATED_ENDING
    assert ws._looks_truncated(long_but_cut_off, word_lo=1100) is True


def test_looks_truncated_false_for_intentional_em_dash_cliffhanger():
    long_cliffhanger = (_REAL_PROSE_HEAD + " ") * 20 + "The door creaked open —"
    assert ws._looks_truncated(long_cliffhanger, word_lo=1100) is False


def test_invalid_prose_reason_prioritizes_meta_commentary_over_truncation():
    # a short response that ALSO looks like meta-commentary should report the
    # meta-commentary defect (it's the more specific / actionable diagnosis).
    reason = ws._invalid_prose_reason(_REAL_META_COMMENTARY_HEAD_1, word_lo=1500)
    assert reason is not None and "planning/analysis notes" in reason


def test_invalid_prose_reason_reports_truncation():
    reason = ws._invalid_prose_reason(_REAL_TRUNCATED_SECTION, word_lo=1500)
    assert reason is not None and "truncated" in reason


def test_invalid_prose_reason_none_for_valid_prose():
    full_length_prose = (_REAL_PROSE_HEAD + " ") * 20
    assert ws._invalid_prose_reason(full_length_prose, word_lo=1100) is None
