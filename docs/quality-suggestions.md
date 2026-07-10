# Novel quality & consistency — 100 suggestions

Grounded in a full investigation of the noveliser2 pipeline (`src/pipeline.py`,
`src/write_section.py`, `src/retrieval_memory.py`, `src/craft.py`, `src/models.py`,
`src/brain.py`), git history of the removed `fact_ledger.py` (commit `80e0529`), a
close read of a completed real novel (`output/The_Weight_of_Silent_Things/`, 10
chapters × 10 sections), and a literature/practitioner survey of LLM long-form
fiction generation (RecurrentGPT, Re3/DOC, Dramatron, Agents' Room, NovelCrafter
Codex, temporal-validity-in-RAG research).

## Key grounded findings (why these two problems exist)

- **Consistency**: `retrieval_memory.py` embeds every section's sentences into one
  flat, unweighted pool. `write_section.py` builds its retrieval query from
  `section.goal + section.key_events + character names` (not "Bob's dog breed"),
  retrieves only the top `RETRIEVAL_K=12` (write_section.py:15) sentences by cosine
  similarity, and the model is merely *asked* (not forced) not to contradict them.
  Character sheets (`models.py` `Character`) are built once by `create_characters`
  and **never updated** as the book progresses (pipeline.py:90-93, 244-253). A
  stale fact and a corrected fact are equally "similar" in embedding space — there
  is no notion of "current truth." `SectionResult.new_facts` is a dead field,
  always hardcoded empty (write_section.py:58, pipeline.py:174). The prior
  `fact_ledger.py` (structured subject/attribute/value store + contradiction
  detection + regenerate-on-contradiction) was removed specifically because it cost
  ~2.6 full prose regenerations per section — a real cost problem, not a wrong idea.
- **Quality**: every pipeline stage, including 1500-2000-word prose generation, runs
  on one fixed cheap tier (`Tier.FREE_FAST`, brain.py:13) with no escalation. There
  is **no revision, self-critique, editing, or quality-scoring pass anywhere** in
  `src/`. Word target is a flat 1500-2000 words regardless of scene pacing. POV/tense
  voice is free text with no enforcement. No banned-cliche list beyond a tiny
  "CUT THESE" reminder in `PROSE_CRAFT`. No human-curated prose exemplars — only
  2-3 abstract LLM-generated example sentences.
- **Real symptoms found in a finished novel**: a near-duplicate section
  (chapter_10_section_7 vs chapter_10_section_8, 94% textually identical,
  `SequenceMatcher` ratio 0.942) where a planned plot beat ("a sudden letter... a
  ghost from her past") silently never happened; outline/prose drift (the outline's
  inciting incident, "a restored kiln shard," never appears in chapter 1 prose); a
  character-name typo ("El's breath hitched" instead of "Elara's"); heavy formulaic
  phrase reuse ("His eyes were dark, [adjective], [verb]-ing" in 7+ sections); and
  motif overuse ("the weight of" ×217, "ghost" ×245, "breath hitched" ×11 across
  100 sections).

---

## A. Consistency / continuity (1–35)

1. Reintroduce a **lightweight structured fact ledger** alongside (not replacing)
   `retrieval_memory.py`: a small `dict[entity][attribute] -> (value, section_id)`
   table for high-value, easily-tracked facts (names, physical descriptions, pet
   breeds/names, relationships, locations, ages, injuries). Update it via ONE cheap
   structured-extraction call per section (`chat_structured`, small schema) rather
   than the old approach's full regeneration loop — this avoids the cost blowup that
   got `fact_ledger.py` removed while keeping the "current truth" guarantee.
2. Inject the fact ledger's relevant entries into `write_section`'s prompt as a
   short, authoritative "CANON FACTS (do not contradict)" block, separate from and
   preceding the soft "ESTABLISHED DETAILS" retrieval list.
3. Make ledger facts **section-stamped** so "as of chapter N" is explicit — enables
   surfacing the *most recent* value, not a similarity-ranked guess.
4. When the extraction call detects a value conflicting with an existing ledger
   entry (e.g. dog breed changed), do NOT auto-regenerate the section (too costly);
   instead flag it in a `continuity_warnings.json` for a human/automated review pass
   (see #7).
5. Extend `Character` model fields (models.py) with a small set of "hard" tracked
   attributes (name, key physical trait, notable possession/pet) populated at
   character creation and treated as immutable canon unless the outline explicitly
   plans a change.
6. Add a dedicated **post-generation consistency-check pass** run once after the
   whole novel (or per chapter) completes: a cheap LLM call comparing pairs/groups
   of chapters' fact-ledger snapshots and flagging contradictions in a report file
   — cheaper than in-line regeneration, and still catches drift before EPUB export.
7. Build a small CLI/step (`check_continuity.py`) that runs the pass in #6 and
   prints a human-readable diff report; wire it into `pipeline.py` as an optional
   final stage, non-blocking (never abort the run, just report).
8. Increase `RETRIEVAL_K` (write_section.py:15) from 12, or make it adaptive
   (scale with number of prior sections) so late-chapter sections aren't starved
   for context in an ever-growing embedding pool.
9. Add **recency weighting** to `RetrievalMemory.retrieve` (retrieval_memory.py) —
   blend cosine similarity with a decay/boost favoring the most recent section
   mentioning an entity, since "most recent" usually beats "most similar" for facts
   that can change (a corrected value is often LESS similar in phrasing than the
   original).
10. Add **entity-level deduplication** in the retrieval store: when multiple
    sentences describe the same (entity, attribute) pair, keep only the latest
    and drop older ones from the general similarity pool (they remain in the fact
    ledger for provenance).
11. Broaden the retrieval query construction (write_section.py:47) to explicitly
    include named entities from the *character sheet* (not just section goal/key
    events text), so a section that doesn't happen to mention "the dog" in its
    goal still retrieves dog-related established sentences if a character with a
    dog appears in the scene.
12. Raise the sentence length floor/truncation (retrieval_memory.py: drops <25
    chars, truncates at 400) carefully — very short factual sentences ("Rex was a
    beagle.") are exactly the kind of thing getting dropped or truncated; audit
    and adjust thresholds so short factual sentences survive.
13. Pass more than the last 8000 characters of raw running text (write_section.py:
    36-39) as context — increase to a full chapter or use a rolling chapter
    summary plus the last N sections in full, so short-range consistency doesn't
    rely solely on retrieval.
14. Add a **chapter-level structured summary** step (RecurrentGPT-style
    short-term/long-term memory split) generated after each chapter, capturing
    "what just happened / current state of each POV character," fed into every
    subsequent chapter's section-writing prompt as a compact anchor distinct from
    the sentence-embedding pool.
15. Persist and surface the **outline's planned beats** at section-writing time,
    and after writing, run a cheap check comparing the beat that was planned vs.
    what the model claims it wrote (self-report), flagging drops like the "ghost
    from her past" beat that silently vanished in chapter 10.
16. Detect and prevent **near-duplicate sections** directly: after writing a
    section, compute textual similarity (e.g. difflib ratio) against the
    immediately preceding section; if above a threshold (e.g. >0.6), treat it as a
    generation failure and retry that section once with an explicit
    "do not repeat the previous scene" instruction — this would have caught the
    94%-duplicate chapter 10 sections 7/8.
17. Add a **section-freshness guard**: before caching a completed section, check
    the new prose for verbatim multi-sentence overlap with any prior cached
    section (cheap string containment check on N-gram shingles), refusing the
    cache and retrying if found.
18. Make `SectionResult.new_facts` (currently dead, always empty) a real field:
    have the prose-writing call also emit (in the same structured response) a
    short list of new/changed facts it introduced, feeding directly into the
    ledger from #1 without a second LLM call.
19. Track **character state deltas** explicitly (injuries, emotional arc stage,
    relationship status) as part of the fact ledger, since these are exactly the
    kind of "changes over time" detail current architecture has no way to
    represent (vs. static Character sheet).
20. Add a lightweight **timeline tracker**: extract explicit time references
    (dates, "three days later", seasons) per section into a simple ledger so
    the model/validator can catch impossible timeline jumps.
21. When resuming via `continue`, rebuild the fact ledger from cached section
    JSONs the same way `RetrievalMemory.ensure_section` already idempotently
    rebuilds the embedding index (retrieval_memory.py) — keep the new mechanism
    consistent with the existing resumable-checkpoint architecture.
22. Store the fact ledger as its own cached JSON (`output/<Title>/fact_ledger.json`)
    following the existing `record()` checkpoint convention, so it's inspectable
    and resumable like every other pipeline artifact.
23. Add unit/integration tests for the new fact-ledger extraction + retrieval-
    weighting logic (real embedding calls per project convention, skip cleanly
    when arbiter unreachable) — pin a regression test around the specific
    "dog breed drift" failure mode with a synthetic 3-section fixture.
24. Add a regression test that replays the real captured
    `output/The_Weight_of_Silent_Things/chapter_10_section_{7,8}.json` scenario
    (or a trimmed synthetic reconstruction with the same shape) to prove the
    near-duplicate detector (#16/#17) actually catches it.
25. Consider bumping `Tier.FREE_FAST` to a stronger tier specifically for the
    cheap structured fact-extraction call in #1 (structured output correctness
    matters more here than raw prose fluency), while keeping prose generation on
    the existing tier for cost — a "right-sized model per stage" split.
26. Cap total fact-ledger size / prune low-salience facts (e.g. one-off scenery
    details) so the ledger stays a small, high-signal "canon facts" list, not
    another firehose.
27. Surface the character sheet's "hard" attributes (name spelling, pet name,
    pet breed) as a literal do-not-alter reminder appended verbatim at the top of
    every `write_section` prompt, cheap and directly addresses the "golden
    retriever → beagle" example — this needs no new infrastructure and can ship
    immediately.
28. Add explicit **spelling/name-consistency enforcement**: inject the exact
    canonical spelling of every named character at the top of the prompt (would
    have prevented the "El's" vs "Elara's" typo found in chapter_10_section_5).
29. When enhancing the outline (`enhance_outline.py`), persist any concrete
    named objects/props introduced there (e.g. "kiln shard") into the fact ledger
    immediately, so section 1 can be checked against whether it actually
    introduces the planned inciting object — catches outline/prose drift early
    instead of discovering it only via cross-book inspection.
30. Add a **plan-vs-prose drift check** per section: after writing, do a cheap
    structured comparison of `section.key_events`/goal against what got written,
    and log (not block) sections whose written content diverges significantly
    from plan — surfaces problems like the dropped kiln-shard inciting incident
    without adding regeneration cost.
31. Version the character sheet: when the outline calls for a deliberate change
    (a character's stated appearance/possession changing as a plot point), record
    it as an explicit, intentional ledger update tied to a section id — so
    intentional change is distinguishable from accidental drift both to the model
    and in later human review.
32. Extend retrieval to use **maximal marginal relevance** instead of pure top-k
    cosine, so the 12 slots aren't dominated by near-duplicate phrasings of the
    same fact, leaving room for other established details.
33. Log retrieval hits/misses per section (which established-detail sentences
    were actually retrieved) to a debug artifact, so continuity failures can be
    diagnosed after the fact by checking whether the right fact was even
    retrieved vs. was retrieved-but-ignored.
34. Add a minimal "protagonist pet/prop bible" auto-generated at character-
    creation time whenever a character is given a named pet/possession in early
    prompts — currently these are freeform prose from character creation and not
    tracked as a first-class fact at all.
35. Document the new continuity architecture (ledger + retrieval + drift checks)
    in CLAUDE.md, replacing the current "NOT an LLM fact-ledger" framing with an
    accurate description of the hybrid approach, and explain the cost lesson
    learned from the original fact_ledger.py removal so it isn't blindly
    reintroduced at full cost again.

## B. Prose quality / engagement (36–75)

36. Add a **single revision/self-critique pass per section**: after the initial
    prose call, run one additional cheap call that critiques the draft against a
    short rubric (show-vs-tell, voice distinctness, cliché density, hook strength)
    and requests only targeted line edits — not a full regeneration — keeping
    cost close to the current single-call budget while catching the biggest
    quality issues found in the real output (formulaic phrasing, motif overuse).
37. Add an explicit, larger **banned-phrase/cliché list** to `PROSE_CRAFT`
    (craft.py) beyond the current small "CUT THESE" set, informed directly by
    what was actually found in the real novel: "the weight of," "ghost,"
    "breath hitched," and templated constructions like "His eyes were
    [adjective], [verb]-ing."
38. Add a **repetition guard**: before caching a section, grep the running
    manuscript-so-far for the section's most distinctive multi-word phrases; if
    a phrase already appears N+ times across the book, instruct a targeted
    rewrite of that sentence rather than accepting it — directly targets the
    "the weight of" ×217 / "ghost" ×245 problem quantified in the real output.
39. Track **per-character dialogue/voice fingerprints** (vocabulary quirks,
    sentence length, verbal tics) established in `create_characters`, and inject
    them per-POV-character into `write_section` so characters stop "all sounding
    the same" — currently there is no such mechanism (craft audit confirmed:
    "No per-character dialogue/voice differentiation instruction beyond generic
    'characterful... layered with subtext'").
40. Provide **human-curated prose exemplars** (a handful of real published-prose
    excerpts matching different genres/tones) instead of the current 2-3
    abstract LLM-generated example sentences in `WritingStyle` — concrete
    mentor-text beats an abstract style description for getting a model to
    actually write well.
41. Make the **word-count target adaptive** per scene type/pacing beat instead
    of the current flat 1500-2000 words for every section (write_section.py:133)
    — a tense confrontation scene and a slow reflective scene shouldn't be
    forced to the same length; use `Section.scene_type`/pacing fields (already
    present per craft.py's scene-vs-sequel work) to vary the target.
42. Turn POV/tense into a **structured, enforced field** rather than free text
    in `WritingStyle.voice` — pass POV character and tense explicitly per
    section (derivable from the outline) instead of relying on the model to
    self-apply a text description consistently across 100 sections.
43. Add a **per-section opening/closing-hook check**: cheap rubric scoring
    whether the section starts with a hook and ends with a pull-forward (per
    "Unputdownable Fiction" craft doctrine already documented in
    `docs/unputdownable-fiction.md` but not currently enforced/measured anywhere).
44. Add an **LLM-as-judge scoring pass** producing a numeric 0-5 rating with
    textual justification per section (voice, pacing, show-vs-tell, hook), stored
    alongside the section JSON — makes prose quality measurable over time and
    across runs instead of purely subjective.
45. When the judge score (#44) falls below a threshold, allow ONE targeted
    revision retry (not full regeneration) focused on the specific flagged
    weakness — bounded cost, meaningfully raises the floor.
46. Escalate the **prose-writing call specifically** to a stronger model tier
    (if available) while keeping cheaper stages (title, themes, chapter
    breakdown) on `Tier.FREE_FAST` — currently every stage including the actual
    prose the reader experiences runs on the same flat cheap tier
    (brain.py:13), which is backwards for where quality matters most.
47. Add explicit **microtension instructions per paragraph type** (already
    partially covered by `STYLE_INSTRUCTION`) reinforced with concrete "avoid"
    examples pulled from the real novel's actual failure patterns (templated
    physical-description sentences, generic emotional-state naming instead of
    embodied action).
48. Add a **"show don't tell" linter pass**: cheap regex/LLM check flagging
    emotion-naming verbs ("felt," "was overwhelmed with") for optional targeted
    rewrite into embodied action/dialogue.
49. Diversify **sentence-opening patterns**: track a rolling window of recent
    sentence-opening words/structures and nudge the model away from repeating
    the same construction ("His eyes were...") within a short span.
50. Add a **dialogue-density check**: many AI-generated novels drift toward
    dense narration with too little dialogue; measure dialogue-to-narration
    ratio per section and flag sections far outside a healthy range for the
    scene type.
51. Strengthen the outline→section fidelity loop (see #30) so that when a
    planned disaster/turn beat is dropped in prose, it's caught and either the
    section is retried with the beat re-emphasized, or the outline is explicitly
    updated to reflect the change — currently beats can silently vanish (the
    "letter/notification... ghost from her past" beat in chapter 10).
52. Add **chapter-level pacing variance checks**: verify chapters alternate
    scene/sequel and intensity per the craft doctrine's macro-pacing beats
    (already generated in `create_outline`) rather than trusting per-section
    prose calls to independently honor macro pacing with no verification.
53. Expand `craft.py`'s exemplar sentence set to be genre-aware (the current
    style examples are generic; tie them to the book's selected theme/genre
    from `select_themes.py` for more targeted voice guidance).
54. Add a **first-page/opening-chapter quality gate**: since hooking the reader
    in chapter 1 matters disproportionately, run the judge pass (#44) with a
    stricter threshold specifically for chapter 1 section 1.
55. Introduce **scene-goal/conflict explicitness**: ensure every section's
    prompt states the POV character's concrete scene-level want and the
    obstacle, not just the higher-level key_events list — sharpens
    scene-vs-sequel structure already conceptually present in craft.py.
56. Add **antagonist/opposition-force tracking** as a first-class element
    (currently the investigation found no explicit antagonist-pressure
    mechanism) so tension doesn't flatten in the back half of the book.
57. Vary **paragraph rhythm** explicitly: instruct occasional very short
    (one-line) paragraphs for emphasis, since uniform paragraph length is a
    known "AI prose" tell.
58. Add a **cliché-adjective density metric** (adjectives like "dark", "soft",
    "quiet" repeated per page) computed post-generation and fed back as a
    craft-prompt reminder for the next section if trending high.
59. Introduce **setting/sensory-detail rotation**: track which senses
    (sight/sound/smell/touch/taste) were used recently and nudge variety,
    since prose can lean heavily visual by default.
60. Add explicit **chapter title/epigraph or scene-break conventions** if
    genre-appropriate, giving each chapter a stronger sense of shape.
61. For character introductions, enforce **specific, non-generic physical/
    behavioral detail** requirements (one concrete unique trait per major
    character) rather than leaving it to the model's default generality.
62. Add **secondary-character consistency** checks: minor characters
    introduced once should have their basic descriptors (age, role, one trait)
    captured in the fact ledger (#1) too, not just protagonists.
63. Track and avoid **repeated metaphor families** (the real novel leaned on
    "weight," "ghost," "breath" heavily) — extend the repetition guard (#38) to
    flag overused *thematic* metaphors, not just literal phrases.
64. Add a **synonym/variation pass** for the most-repeated structural
    sentence pattern found (#37) so the model has concrete alternative
    constructions to draw from, not just a "don't do X" instruction.
65. Give the model an explicit **prior-section-ending recap** (last 1-2
    sentences of the previous section, always, regardless of the 8000-char
    window) so scene transitions are smooth even for long chapters where the
    prior section falls outside the truncated window.
66. Add a lightweight **beta-reader-style final pass** across the whole
    finished manuscript (or per chapter) that flags the top N quality issues
    for a human to optionally address — a cheap wrap-up report, not a blocking
    gate, complementing #6's continuity report with a craft-quality report.
67. Track a running **"used similes/metaphors" list** and instruct the model
    to avoid reusing any of them verbatim — a stronger, structured version of
    #63.
68. Consider a **two-pass outline** (rough pass → refined per-chapter pass
    informed by what's already written), per the "dynamic hierarchical
    outlining" technique found in the literature survey — mitigates the
    static-outline coherence decay documented in academic long-form-generation
    research (Re3/DOC).
69. Where `enhance_outline.py` already exists, verify/extend it to also
    inject foreshadowing/payoff pairing (plant early, pay off later) as an
    explicit structured field consumed by later chapters' section prompts.
70. Add explicit **stakes-escalation tracking** across chapters (a simple
    1-10 tension-level field per chapter in the outline) so pacing can be
    checked/enforced rather than assumed.
71. For humor/voice genres, consider genre-specific craft blocks in craft.py
    (currently craft instructions are largely genre-agnostic) selected based
    on `select_themes.py` output.
72. Add a **word-choice register consistency check** (contemporary vs.
    period-appropriate vocabulary) if the novel has a specified setting/era —
    currently nothing validates anachronistic word choices.
73. Make the "CUT THESE" list (craft.py) empirically driven: periodically
    (or via a script) scan completed novels' output for the most overused
    words/phrases and feed that list back into `PROSE_CRAFT` as a living,
    updated ban list rather than a fixed hardcoded set.
74. Build a small internal tool/script (`analyze_novel.py`) that runs the
    repetition/motif/cliché metrics used in this investigation (phrase
    frequency, near-duplicate section detection, adjective density) against
    any `output/<Title>/` directory, so quality regressions are measurable
    on every future run, not just discovered by manual inspection.
75. Wire `analyze_novel.py` (#74) into the pytest suite as an opt-in quality
    smoke-test against a fixture novel, catching regressions in the craft
    prompts over time (skip cleanly if no fixture output exists locally).

## C. Architecture, process & pipeline hygiene (76–100)

76. Fix the **dead `SectionResult.new_facts` field** (write_section.py:58,
    pipeline.py:174) — either wire it to the new fact-ledger flow (#18) or
    remove it; a hardcoded-empty field masquerading as active is a correctness
    smell independent of the quality work.
77. Add integration tests directly reproducing the **chapter_10 near-duplicate
    bug class**: assert that two consecutively generated sections for the same
    chapter are not near-textual-duplicates (uses #16/#17's detector).
78. Add a regression test asserting **outline-introduced named objects
    actually appear** in the chapter they're planned for (using #29/#30's
    drift tracking), grounded in the real "kiln shard never appears" finding.
79. Audit and test **name-typo resistance**: a test that seeds a character
    with a name prone to truncation-prompted typos (e.g. a name whose prefix
    is itself a plausible short name, like "Elara"/"El") and asserts the
    canonical spelling is preserved (grounded in real "El's" vs "Elara's" bug).
80. Ensure new fact-ledger/quality-scoring artifacts follow the existing
    `record()` checkpoint convention exactly (resumable, skip-if-cached) so
    `continue` semantics remain intact per project architecture.
81. Confirm and document (CLAUDE.md) which concrete model `Tier.FREE_FAST`
    resolves to today, and record the mapping for any new tier used by
    escalated calls (#46), since this was unverifiable from repo code alone
    during investigation (lives in daz-agent-sdk config, outside this repo).
82. Add a `--quality-report` or similar flag to `./run create`/`continue`
    that runs the continuity (#7) and craft (#66) reports on demand without
    re-running generation, useful for iterating on craft.py changes against
    an existing output.
83. Ensure all new model fields (fact ledger entries, judge scores, etc.) on
    `Character`/`Section`/new models are **defaulted** so old checkpoints
    still load, per the existing project convention (Character/Section already
    do this for craft fields).
84. Cap wall-clock/cost impact of new passes explicitly: document in
    CLAUDE.md the added cost-per-section (extraction call + optional judge
    call + optional revision retry) versus the current ~165s/section baseline,
    so future contributors understand the cost/quality tradeoff being made
    (directly addresses why fact_ledger.py was originally removed).
85. Add a feature flag / config toggle to disable the new revision/judge
    passes for fast draft runs (keeping current fast-cheap behavior available
    when a user wants speed over polish).
86. Extend `craft.py`'s constants with clear docstring comments noting where
    each is injected (currently only discoverable by grepping call sites) —
    lowers the barrier for future craft-prompt iteration.
87. Add a small `docs/continuity-architecture.md` documenting the new
    fact-ledger + retrieval hybrid design and its cost rationale, keeping
    CLAUDE.md high-level and the design doc detailed (matches existing
    `docs/unputdownable-fiction.md` pattern).
88. Ensure the new fact-extraction/judge calls **do not silently fail** and
    stall the pipeline if the model call errors — follow existing `brain.py`
    error-handling conventions, never a bare `except: pass`.
89. Verify the new passes' embedding/model calls skip cleanly in tests when a
    backend (boringstack/spark) is unreachable, per existing pytest
    conventions (`pytest src`).
90. Run `ruff check src/` after every implementation batch, not just at the
    end, so lint issues are caught close to the change that introduced them.
91. Add a small CLI utility to **inspect the fact ledger** for a given
    `output/<Title>/` (print current canon facts), useful for debugging
    continuity issues in real runs going forward.
92. Where multiple new pipeline stages are added (fact extraction, judge
    scoring, drift check), keep them as clearly separate, individually
    toggle-able functions rather than one monolithic "quality" mega-function —
    honors DRY/KISS and keeps future maintenance tractable.
93. Reuse existing `chat_structured` machinery (brain.py) for all new
    structured extraction/scoring calls rather than inventing a parallel
    prompting mechanism — consistent with existing character/outline
    generation patterns already in the codebase.
94. Avoid duplicating logic between the new continuity-drift checker (#30)
    and the near-duplicate detector (#16/#17) — factor shared "compare two
    text blobs" utilities into one helper module.
95. Keep the retrieval-memory sentence-embedding mechanism as the PRIMARY
    consistency signal for soft/atmospheric continuity (unchanged), and treat
    the new fact ledger as a narrow, additive layer only for high-value hard
    facts — avoids the trap of rebuilding a full parallel system, per the
    project's DRY/KISS/YAGNI directive.
96. After implementing, benchmark end-to-end time-per-section before/after
    the new passes on a short real run, and record the delta in CLAUDE.md so
    future users know what to expect.
97. Confirm EPUB generation (`epub_generator.py`) is unaffected by any new
    intermediate artifacts (fact ledger, judge scores) — those should be
    pipeline-internal and not leak into the reader-facing output.
98. Add a short "known limitations" section to CLAUDE.md explicitly stating
    what the new mechanism does NOT catch (e.g. long-range thematic
    inconsistency, subtle characterization drift) — avoids overselling the
    fix and manages expectations honestly.
99. After implementation, do a real `./run create` short test (2-3 chapters,
    2 sections/chapter) with a character who has a memorable, trackable
    detail (e.g. a named pet with a specific breed) mentioned in chapter 1,
    and manually confirm it's referenced correctly and consistently by the
    final chapter — a direct, concrete proof the fix works, not just a code
    review.
100. Revisit and update `docs/unputdownable-fiction.md` itself if any of the
     above changes contradict or extend its guidance (e.g. add a
     "continuity & revision" section covering the new ledger/critique passes),
     keeping the craft doctrine document and the actual pipeline in sync —
     the investigation found the doctrine doc and code already drifted once
     (aspirational vs. wired-in craft blocks); don't let that recur here.
