![](banner.jpg)

# Noveliser2

AI-powered novel generation. Give it a one-sentence description of a story and it produces a complete novel as an EPUB, with cover art and chapter illustrations.

## What It Does

Noveliser2 takes a brief description of a novel and autonomously generates:

- A title
- Plot structure, themes, and characters
- A detailed outline
- A persistent style sheet: viewpoint distance, character voices, rhythm, imagery, worked examples and revision guidance
- Full prose for every chapter and section, with evidence-based checks for repetitive rhetorical habits
- A cover image and chapter illustrations
- A finished EPUB, Markdown manuscript and clean audiobook narration script
- Optional resumable remote narration, assembled into a chaptered M4B audiobook

Generation is resumable — if interrupted, you can pick up where you left off.

## Prerequisites

- Python 3.12+
- The configured agentd3 daemon for planning and prose; remote Arbiter for embeddings/narration
- The configured image service for generated artwork
- `ffmpeg` and `ffprobe` for M4B export

Non-secret settings belong in gitignored `local/config.toml`; credentials use daz-secrets, never environment variables. No local language model is loaded.

## Installation

```bash
git clone <repo-url> ~/src/noveliser2
cd ~/src/noveliser2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optionally, create a global shortcut:

```bash
mkdir -p ~/bin
echo '#!/bin/bash' > ~/bin/noveliser2
echo 'exec ~/src/noveliser2/run "$@"' >> ~/bin/noveliser2
chmod +x ~/bin/noveliser2
```

## Usage

### Create a Novel

```bash
./run create "A retired clockmaker discovers that a mysterious antique pocket watch can show glimpses of alternate timelines."
```

By default this generates a 10-chapter novel with 10 sections per chapter. You can customise the size:

```bash
./run create "Your story idea" --chapters 5 --sections 4
```

Set a custom author name:

```bash
./run create "Your story idea" --author "Jane Smith"
```

### Style and revision

Use `--style "your voice brief"` to steer a book. The directive survives resume. Every scene receives the full saved style sheet, including positive examples and character-specific dialogue choices. Older checkpoints retain their existing decisions and receive missing fields through a cached enrichment step.

The standing guidance and calibrated checks target **repetition**, not a ban on literary devices: recurring triads, corrective antithesis, stock body language, polished therapist/debate dialogue, mixed imagery and explanatory morals. A flagged scene gets at most one revision; the original remains when the revision fails structural checks or does not reduce the measured excess. These are editorial heuristics, not an authorship detector. See [the source-linked research](docs/ai-prose-research.md) and `src/craft.py`.

### Export ebook and audiobook

Every completed generation now writes `book.json`, `manuscript.md`, an EPUB and a UTF-8 `.narration.txt`. They share the same chapter prose. The single-narrator script retains dialogue tags and removes explicit production directions; it does not invent speaker assignments.

```bash
./run export-book "output/My_Book/book.json"
./run export-book "output/My_Book/book.json" --audio --icloud --books
```

`--audio` submits real remote Kokoro work. Exit **3** means pending: rerun the same command later to resume persisted jobs and completed chunks. No local fallback occurs on failure. The completed M4B has chapter navigation, AAC audio and a verification report. Input coverage, WAV frames, durations, chapter timing and full AAC decode are checked; those checks cannot guarantee every pronunciation.

Example `local/config.toml`:

```toml
[agentd3]
api_base = "http://127.0.0.1:8620"

[backend]
backend = "sdk"

[audiobook]
base_url = "http://10.0.0.254:8400"
voice = "bf_emma"
speed = 0.98
```

`--icloud` makes SHA-256-verified **local** copies under iCloud Drive/Books/<Title>. It does not by itself prove server upload. `--books` requests EPUB/M4B import into macOS Books; library verification is separate. `delivery.json` records these distinctions.

### Resume an Interrupted Novel

If generation is interrupted, resume it by title:

```bash
./run continue "The Clockmaker's Paradox"
```

### List Novels

See all completed novels:

```bash
./run list-finished
```

See all in-progress novels:

```bash
./run list-ongoing
```

### Quick Test

Generate a minimal 1-chapter novel to verify everything works:

```bash
./run test
```

Generate a slightly larger 3-chapter test novel:

```bash
./run test_bigger
```

### Run Quality Checks

```bash
./run check
```

## Output

Generated novels are saved under `output/<Title>/`, with cover art, chapter illustrations, an EPUB, `book.json`, `manuscript.md` and a narration script. Audio export adds an M4B, its verification JSON and restart-safe synthesis checkpoints.

`./run deploy` installs the local `~/bin/noveliser2` CLI against the canonical checkout and verifies it with `./run health`. There is no persistent noveliser daemon to restart.

## License

This project is licensed under [CC BY-NC 4.0](https://darren-static.waft.dev/license) - free to use and modify, but no commercial use without permission.
