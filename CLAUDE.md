# noveliser2 — AI novel generator

Entry point: `./run create "<description>" [--title "Exact Title"] --chapters N --sections M --author "Name"`.
`--title` forces the title (else step 1 generates one). `--cover <path>` adopts an
existing image as the book cover (converted to cover.jpg, no generation). `continue
"<title>"` resumes.
Output goes to `output/<Title>/`; every pipeline step caches a JSON there and `record()`
skips completed steps, so runs are fully resumable (checkpoint files are raw model dumps,
not wrapped). The process calls `setproctitle("noveliser2")`, so `pgrep -f "run create"`
will NOT find it once running — pgrep `noveliser2` or capture `$!`.

## Model / backend routing
- Text: `brain.py` calls daz-agent-sdk `agent.ask(tier=Tier.FREE_FAST)` for structure and
  `Tier.FREE_THINKING` for prose. Both tiers are set in `~/.daz-agent-sdk/config.yaml` and
  now head with `arbiter:qwen3.6-35b` — the arbiter (spark, http://spark:8400) dispatches
  the job to any of its registered placements (spark-ollama / boringstack / darrens-mbp),
  so generation is machine-agnostic and survives any one box being down. Fallbacks:
  direct `boringstack:qwen3.6:35b-a3b` (Ollama at 10.0.0.42 — DHCP; if unreachable check
  the asus router's dnsmasq leases for "boringstack"), then localhost Ollama.
  `chat`/`chat_structured` take an optional `tier=` override. Verified: plain, structured,
  and thinking calls all return `model_used.provider == "arbiter"`.
- Images: `generate_images.py` calls `agent.image()` (no provider) → codex provider.
- Embeddings: `agent.embed()` → arbiter on spark (10.0.0.254). 768-dim.
- The SDK is **editable-installed** in `.venv` (`python -m pip install -e ~/src/daz-agent-sdk
  --no-deps`; `--no-deps` because of the local-only `arbiter-client` dep). The venv's
  `bin/pip` shebang is broken (venv was relocated from /Volumes/T9) — always use
  `.venv/bin/python -m pip`.

## Plot architecture (primary + subplots as standalone short stories)
Between character creation and outlining, the pipeline plans one PRIMARY plot plus
N subplots (`create_plots.subplot_count` = max(1, min(4, chapters//3))), writes each
plot as a **standalone short story** sequentially — each story's prompt embeds all
previously written ones verbatim with a no-contradiction requirement — then derives
per-character **before/after arcs** (`character_arcs.py`; change_kind may be growth,
decline, corruption, redemption, flat, or terminal). The outline stage receives the
full stories + `PLOT_WEAVE_INSTRUCTION`; chapter breakdown must name which thread each
chapter advances and resolve every thread; every section prompt carries compact
PLOT THREADS + CHARACTER TRAJECTORIES blocks. craft.py's render helpers are duck-typed
(accept pydantic models OR resume-checkpoint dicts). record() steps: "Create plot plan",
"Write plot story N", "Create character arcs".

## Continuity = retrieval memory + lightweight fact ledger
`retrieval_memory.py`: after each section, every sentence is embedded (remotely, on
spark) and stored; `write_section` retrieves the most relevant prior sentences as
"established details" (recency-weighted). `fact_ledger.py` (the CHEAP reintroduction —
one FAST-tier extraction call per section, advisory-only, never regenerates prose)
keeps hard canon facts (breeds, ages, relationships) in an entity→attribute store
injected as an authoritative CANON FACTS block; conflicts are logged to
`continuity_warnings.json`, never acted on inline. Both rebuild idempotently on resume.
Per section ≈ two boringstack prose calls (draft + revision pass, ~165s each) + one
cheap extraction + remote embeds.

## Craft
`craft.py` holds the distilled "Unputdownable Fiction" manual (`docs/unputdownable-fiction.md`)
as prompt blocks injected into the stages: character engine (Wound/Lie/Want/Need/arc) +
voice fingerprints in `create_characters`, macro pacing beats + stakes escalation +
dramatic irony in `create_outline`, chapter-ending hooks in `break_into_chapters`,
scene-vs-sequel + disaster in `break_into_sections`, microtension/pacing in
`define_writing_style`, and the full prose crucible (banned clichés measured from real
output, contradiction-based subtext, concrete-over-abstract) in `write_section`.
`Character` and `Section` gained matching model fields (all defaulted, so old
checkpoints still load).

## Generation guards (write_section.py)
The reasoning PROSE_TIER sometimes emits its own planning notes as the whole response
(no think-tags) or truncates mid-sentence; `_invalid_prose_reason` detects both and
retries once same-tier, once on the non-reasoning tier, then raises. A near-duplicate
guard retries once on section-vs-previous similarity. `_revise_prose` (ON by default)
fixes overused phrases and MUST-ADD missing planned beats — its carve-out wording is
load-bearing: a blanket "don't change events" instruction silently defeats the
weave-in request. Dropped-beat detection is two-stage: keyword prefilter
(`find_dropped_beats`) then semantic confirmation (`confirm_dropped_beats`, one
FAST-tier call) because keyword overlap cannot tell a dropped beat from a
paraphrased one. `retrieval_memory._embed` retries transient arbiter failures.

## Worktree gotcha
Git worktrees of this repo have NO `.venv`; `./run` only self-activates when `.venv`
exists locally. From a worktree run the parent checkout's interpreter against the
worktree's `./run`: `VIRTUAL_ENV=/Users/darrenoakey/src/noveliser2/.venv
/Users/darrenoakey/src/noveliser2/.venv/bin/python ./run ...` (the editable-installed
SDK import works because it resolves to ~/src/daz-agent-sdk).

## MEMORY / hardware safety (important)
This Mac is RAM-constrained (~69GB, often near-full from other services) and has OOM-rebooted
when a big model was loaded locally. NEVER load an LLM on this machine: prose runs on
boringstack, embeddings on spark — both remote. Localhost Ollama small models are also SLOW
here (CPU/contended), so don't route extraction there either. boringstack is a 137GB Apple
Silicon box; spark is the CUDA arbiter. Quality gate: `ruff` (`.venv/bin/python -m ruff check
src/`) + `pytest src` (embedding/model tests skip cleanly when a backend is unreachable).
