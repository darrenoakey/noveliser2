# noveliser2 — AI novel generator

Entry point: `./run create "<description>" [--title "Exact Title"] --chapters N --sections M --author "Name"`.
`--title` forces the title (else step 1 generates one). `continue "<title>"` resumes.
Output goes to `output/<Title>/`; every pipeline step caches a JSON there and `record()`
skips completed steps, so runs are fully resumable (checkpoint files are raw model dumps,
not wrapped). The process calls `setproctitle("noveliser2")`, so `pgrep -f "run create"`
will NOT find it once running — pgrep `noveliser2` or capture `$!`.

## Model / backend routing
- Text: `brain.py` calls daz-agent-sdk `agent.ask(tier=Tier.FREE_FAST)`. The active model is
  set in `~/.daz-agent-sdk/config.yaml` — currently `boringstack:qwen3.6:35b-a3b` (a remote
  Ollama box at 10.0.0.237). `chat`/`chat_structured` take an optional `tier=` override.
- Images: `generate_images.py` calls `agent.image()` (no provider) → codex provider.
- Embeddings: `agent.embed()` → arbiter on spark (10.0.0.254). 768-dim.
- The SDK is **editable-installed** in `.venv` (`python -m pip install -e ~/src/daz-agent-sdk
  --no-deps`; `--no-deps` because of the local-only `arbiter-client` dep). The venv's
  `bin/pip` shebang is broken (venv was relocated from /Volumes/T9) — always use
  `.venv/bin/python -m pip`.

## Continuity = retrieval memory (NOT an LLM fact-ledger)
`retrieval_memory.py` is the consistency mechanism: after each section, every sentence is
embedded (remotely, on spark) and stored; `write_section` retrieves the most relevant prior
sentences and injects them as "established details", alongside the structured character sheet.
There is no per-section LLM fact-extraction or contradiction-regeneration (the old
`fact_ledger.py`, removed). `RetrievalMemory.ensure_section` is idempotent so resume rebuilds
the index from cached sections. Per section ≈ one boringstack prose call (~165s) + cheap
remote embeds.

## Craft
`craft.py` holds the distilled "Unputdownable Fiction" manual (`docs/unputdownable-fiction.md`)
as prompt blocks injected into the stages: character engine (Wound/Lie/Want/Need/arc) in
`create_characters`, macro pacing beats + therefore/but in `create_outline`, scene-vs-sequel +
disaster in `break_into_sections`, microtension/pacing in `define_writing_style`, and the full
prose crucible in `write_section`. `Character` and `Section` gained matching model fields
(all defaulted, so old checkpoints still load).

## MEMORY / hardware safety (important)
This Mac is RAM-constrained (~69GB, often near-full from other services) and has OOM-rebooted
when a big model was loaded locally. NEVER load an LLM on this machine: prose runs on
boringstack, embeddings on spark — both remote. Localhost Ollama small models are also SLOW
here (CPU/contended), so don't route extraction there either. boringstack is a 137GB Apple
Silicon box; spark is the CUDA arbiter. Quality gate: `ruff` (`.venv/bin/python -m ruff check
src/`) + `pytest src` (embedding/model tests skip cleanly when a backend is unreachable).
