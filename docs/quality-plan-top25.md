# Top 25 — chosen implementation plan

Synthesized from a 6-seat council (Architect, Pragmatist, Skeptic, Maintainer,
Contrarian, Designer) reviewing `docs/quality-suggestions.md`. All six seats
independently converged hard on a small core set: #1/#2/#9/#16/#27/#28/#37/
#38/#41/#46 appeared in every single seat's list. That consensus, plus the
Skeptic's specific trap warnings, drives the final selection below.

## Selection philosophy

1. **Zero-infrastructure prompt fixes ship first** (#27, #28, #65) — they
   can't break resumability and directly kill the exact bugs found in the
   real novel (dog-breed drift, "El's"/"Elara's" typo).
2. **Detect-and-flag, never regenerate** — this is the specific lesson from
   why the original `fact_ledger.py` was removed (~2.6x cost from
   contradiction-regeneration). Every consistency mechanism here logs or
   annotates; none trigger a full section regeneration loop.
3. **One bounded revision pass, not a chain of judge/critique/retry passes**
   — the Skeptic correctly flagged that #36+#44+#45 as three separate passes
   is 2-3x runtime per section ("death by a thousand passes"). Merged into
   a single gated pass (#36), toggle-able via #85.
4. **Reader-perceptible over dev-only** where there's a choice — Category C
   was trimmed hard (Designer/Contrarian both argued most of 76-98 is
   process theater); only the plumbing that prevents real breakage (old
   checkpoints, silent failures) survives.

### Contested calls, resolved

- **#18 vs #1** (fact extraction coupled to the prose call vs. a separate
  cheap `chat_structured` call): the Skeptic, Architect, and Maintainer all
  independently flagged the same risk — corrupting prose generation or the
  extraction schema by coupling them. **Chose #1** (separate small call).
  #18's underlying goal (stop the dead `new_facts` field) is still achieved,
  just via #1's ledger writing into it rather than the prose call itself.
- **#13** (pass full chapter as context) — Skeptic flagged prompt-bloat/
  attention degradation on a 35B model. **Superseded by #14 + #65** (compact
  chapter summary + prior-section-ending recap) — same continuity benefit,
  bounded prompt size.
- **#17** (unbounded duplicate-retry loop) — Skeptic flagged infinite-loop
  risk on a deterministic-ish model. **Chose #16 only** (bounded to exactly
  one retry).
- **#4, #12** — folded into #1/#30 and #9 respectively as implementation
  details rather than separate top-25 slots, to stay at exactly 25 without
  redundant entries.

---

## Category A — Consistency (12 picks)

1. **#1 — Lightweight structured fact ledger via one cheap extraction call.**
   6/6 seats. Core fix for the dog-breed-drift complaint; avoids the
   regeneration-loop cost trap that killed the original fact_ledger.py.
2. **#2 — Inject ledger facts as a "CANON FACTS" block, separate from the
   soft retrieval list.** 6/6 seats. Makes canon authoritative vs. merely
   suggested.
3. **#3 — Section-stamp ledger facts ("as of chapter N").** Skeptic +
   Maintainer. Gives "most recent" a clear precedence over "most similar."
4. **#9 — Recency weighting in `RetrievalMemory.retrieve`.** 6/6 seats.
   Directly fixes the failure mode where a stale fact is embedding-similar
   to the corrected one. Folds in #12 (stop dropping short factual
   sentences like "Rex was a beagle.") as part of the same retrieval fix.
5. **#11 — Broaden retrieval query construction to include character-sheet
   entities, not just section goal/key-events text.** 4/6 seats.
6. **#14 — Chapter-level structured summary (short/long-term memory
   split).** 4/6 seats, and the Architect's top long-term-shape pick
   (RecurrentGPT-proven pattern). Bounded-size alternative to #13.
7. **#16 — Near-duplicate section guard, bounded to one retry.** 6/6 seats.
   Directly would have caught the real 94%-identical chapter 10 sections
   7/8 bug found in the output-inspection pass.
8. **#21 — Rebuild the fact ledger on `continue` the same way
   `RetrievalMemory.ensure_section` already idempotently rebuilds.**
   Architect + Pragmatist + Skeptic + Maintainer. Keeps the new mechanism
   consistent with existing resumable-checkpoint architecture.
9. **#22 — Fact ledger persisted as its own `record()`-conventional JSON
   checkpoint.** Same 4 seats. Inspectable, resumable, matches every other
   pipeline artifact.
10. **#27 — Inject hard character facts (pet breed/name, physical trait)
    verbatim at the top of every `write_section` prompt.** 6/6 seats. Zero
    infrastructure, ships immediately, directly kills the exact bug the
    user reported.
11. **#28 — Enforce canonical name spelling verbatim in-prompt.** 6/6
    seats. Directly fixes the real "El's" vs. "Elara's" typo found in the
    output audit.
12. **#30 — Cheap, non-blocking plan-vs-prose drift log (planned outline
    beat vs. what was actually written).** 4/6 seats. Would have surfaced
    the silently-dropped "ghost from her past" beat and the "kiln shard"
    outline/prose drift found in the real novel — logged, never blocking.

## Category B — Prose quality / engagement (8 picks)

13. **#36 — One bounded revision/self-critique pass per section**, gated
    behind the feature flag in #85 so cost stays opt-in and capped at
    exactly one extra call (absorbs the intent of #44/#45 — a single pass
    with an inline rubric check, not a separate judge-score call plus a
    separate conditional-retry call). 5/6 seats (Skeptic dissented on cost
    grounds; addressed by making it flag-gated).
14. **#37 — Larger, empirically-grounded banned-phrase list in
    `PROSE_CRAFT`.** 6/6 seats. Targets the measured "the weight of" ×217,
    "ghost" ×245 problem directly.
15. **#38 — Repetition guard against the manuscript-so-far.** 6/6 seats.
    Same measured problem, structural fix rather than just a prompt ban.
16. **#39 — Per-character dialogue/voice fingerprints.** 4/6 seats
    (Pragmatist, Contrarian, Designer, Architect via the craft.py-extension
    group). Addresses "characters all sound the same," which craft.py
    currently has zero mechanism for.
17. **#41 — Adaptive word-count target by scene type/pacing.** 6/6 seats.
    Uses `Section.scene_type`/pacing fields that already exist but
    currently go unused for length.
18. **#42 — Structured, enforced POV/tense field** instead of free text in
    `WritingStyle.voice`. Pragmatist + Contrarian + Designer. Head-hopping
    is immediately reader-visible.
19. **#46 — Escalate the prose-writing call to a stronger model tier**
    while keeping cheap stages on `Tier.FREE_FAST`. 6/6 seats, and called
    "the single dominant fact" by the Contrarian: every stage including
    reader-facing prose runs on one flat cheap tier today.
20. **#65 — Always pass the previous section's literal ending** (not just
    whatever falls inside the 8000-char window) into the next section's
    prompt. 5/6 seats. Cheapest possible fix for section-to-section
    transition smoothness.

## Category C — Architecture / process hygiene (5 picks)

21. **#74 — `analyze_novel.py`: a script computing the repetition/motif/
    duplicate-section metrics used in this investigation, runnable against
    any `output/<Title>/`.** 5/6 seats. Makes quality regressions
    measurable on every future run instead of requiring manual inspection
    (which is how this investigation found the chapter-10 duplicate and
    the ×217 phrase reuse in the first place).
22. **#76 — Fix the dead `SectionResult.new_facts` field** (currently
    hardcoded empty) by wiring it to the #1 ledger write path. Direct
    correctness fix identified in the pipeline trace.
23. **#83 — All new model fields (ledger entries, etc.) must be defaulted**
    so old checkpoints still load. 4/6 seats (Architect, Pragmatist,
    Skeptic, Maintainer) — non-negotiable per the project's existing
    convention and the Maintainer's blast-radius concern.
24. **#85 — Feature flag to disable the new revision pass (#36) and other
    added calls**, keeping current fast/cheap behavior available. 4/6
    seats. Also the mechanism that makes #36's cost acceptable to the
    Skeptic's objection.
25. **#99 — A real short `./run create` test (2-3 chapters, 2 sections)
    with a trackable detail (e.g. a named pet with a specific breed)
    mentioned in chapter 1, manually confirmed consistent by the final
    chapter.** Concrete, direct proof the fix works — not just code
    review. Required by the task's own verification step regardless.

---

## Explicitly excluded (with reason)

- **#18** — superseded by #1 (coupling fact-extraction to the prose call
  risked degrading both; Skeptic/Architect/Maintainer all flagged it).
- **#13** — superseded by #14 + #65 (full raw-chapter context risks
  prompt bloat/attention degradation on the 35B model; a compact summary
  + literal prior-ending recap gets the same benefit safely).
- **#17** — superseded by #16 (unbounded retry-until-fresh loop is an
  infinite-loop risk; one bounded retry suffices and was independently
  chosen by all 6 seats anyway).
- **#44, #45** — merged into #36 as a single bounded pass rather than a
  separate judge-score call plus a separate conditional-retry call, to
  avoid the Skeptic's "2-3x runtime per section" cost objection.
- **#4, #12** — folded into #1/#30 and #9 respectively as implementation
  details of the chosen suggestions, not separate slots.
- **#68 (two-pass dynamic outline)** — Skeptic: invalidates every existing
  checkpoint's resume semantics; too large a blast radius for this pass.
