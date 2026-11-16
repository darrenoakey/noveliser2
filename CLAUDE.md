# noveliser2 — operating notes

Read `AGENTS.md` and `docs/DOCTRINE.md` for the greenline release rules. Never edit the canonical checkout; worktrees share its venv when they lack their own.

## Commands and artifacts

- `./run create "description" --title "Exact Title" --chapters N --sections M --style "voice brief"`.
- `./run continue "Title"` resumes cached stages. The author's directive is saved in metadata.
- Each finished book has an EPUB, `book.json`, `manuscript.md` and a clean `.narration.txt`.
- `./run export-book output/Title/book.json --audio --icloud --books` advances resumable remote narration, produces chaptered M4B, verifies local iCloud copies and requests Books import. Exit 3 means pending: resume the same command later. Do not poll in an agent turn; sleep and inspect the persisted job on wake.
- `./run check` runs ruff and all tests, including real daemon revision/style enrichment and real remote TTS; warnings are errors. Use `.venv/bin/python -m pip`, not the relocated venv's broken pip shebang.
- `./run deploy` installs `~/bin/noveliser2` against canonical source and runs a new-process health check. This CLI has no persistent service to restart.

## Model/configuration routing

`brain.py` uses agentd3 conversations for planning. The default is the same proven Fable fiction model as prose; a broad high-tier route exhausted Gemini quota then stalled on provider failover during live enrichment. `agentd3_client.py` runs persistent prose conversations. Non-secret endpoint/model/backend/narrator configuration belongs in ignored `local/config.toml`; CLI overrides use `configure(...)`, never environment variables. Credentials use daz-secrets references, not inline TOML secrets.

Images use the configured durable Codex image service, never an arbiter image fallback. Embeddings and Kokoro narration run remotely on Spark. NEVER load a local language model on this RAM-constrained Mac. Covers/chapter images are always generated unless a supplied cover is adopted.

## Prose quality and continuity

`docs/ai-prose-research.md` records actual Google/source research and analyzes the user's examples. `craft.py` is the standing positive guidance: selective perception, character-specific diction, scene business/subtext, varied rhythm, coherent imagery and endings without routine morals. `WritingStyle` persists these choices plus worked examples and a revision brief. `define_writing_style.enrich_writing_style` fills missing legacy fields without overwriting existing choices; pipeline records enrichment separately.

`prose_checks.py` counts recurring rhetorical habits. Its corpus-calibrated limits are editorial heuristics, not research findings or an authorship detector. No device is categorically banned. `write_section.py` supplies the entire style sheet each time and permits one targeted revision. It keeps the draft when structural/length/speaker checks fail or measured excess does not fall. Rejected revisions retire the conversation so their invented canon cannot leak into later scenes. New threads receive the accepted prose ending.

Continuity retrieval embeds prior sentences remotely and retrieves established details. `SectionResult.lines` retains model-generated speaker tags; ebook prose and the single-narrator script preserve dialogue attribution rather than inventing post-hoc speaker labels.

Structured model replies can contain literal newlines inside a long JSON string. `brain._extract_json` preserves newline/CR/tab content, rejects other raw controls and requires an object; malformed structure receives one real retry before failure. A captured Fable response in `src/style_samples/responses/` guards this case. Corpus excerpts live under `human/` and `generated/`.

## Publication checks

`book.json` is the authoritative final prose. Re-exporting preserves its exact bytes and provenance when content is unchanged; stable SHA-256 cache identities survive Python restarts. Freeze/review the source before synthesis, and require ebook/audio source checksums to agree. Do not copy a changed chunk's audio just because its index matches.

`audiobook.py` bounds every input, proves ordered text coverage, checks item/frame counts and speaking-rate bounds, validates M4B chapter timing and decodes all AAC. Those checks do not prove every pronunciation. `delivery.json` distinguishes a checksum-verified local iCloud copy from server upload, and an import request from an actual Books library entry. Read Books' SQLite library only; never write it directly.
