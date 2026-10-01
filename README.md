![](banner.jpg)

# Noveliser2

AI-powered novel generation. Give it a one-sentence description of a story and it produces a complete novel as an EPUB, with cover art and chapter illustrations.

## What It Does

Noveliser2 takes a brief description of a novel and autonomously generates:

- A title
- Plot structure, themes, and characters
- A detailed outline
- A defined writing style
- Full prose for every chapter and section
- A cover image and chapter illustrations
- A finished EPUB file ready for any e-reader

Generation is resumable — if interrupted, you can pick up where you left off.

## Prerequisites

- Python 3.12+ and the packages in `requirements.txt` installed in a local venv.
- For local text, a reachable **remote** Ollama server with the chosen models installed. Do not load large models on the laptop or run GPU models outside Spark Arbiter.
- For the optional image route, a configured daz-agent-sdk Mac mini Codex image service. `--skip-images` produces a valid text-only EPUB without waiting for images.

Write machine-local non-secret settings to gitignored `local/config.toml`:

```toml
text_backend = "ollama"
ollama_url = "http://10.0.0.42:11434" # your existing remote Ollama endpoint
planning_model = "ornith-1.5:35b"
prose_model = "ornith-1.5:35b"
skip_images = true
```

Without `text_backend = "ollama"`, Noveliser uses the existing daz-agent-sdk tier configuration. A configured remote model that is unavailable fails rather than silently switching to a different model. `--backend arbiter` is the legacy **image** guard (it disables image generation), not a text-model override.

## Installation

```bash
git clone <repo-url> ~/src/noveliser2
cd ~/src/noveliser2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
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
python -m ruff check src/ run scripts/
```

New chapter/section plans contain structured causes, stakes, choices, costs, reversals, state changes and setup/payoff IDs; structurally deficient generations are retried with specific feedback up to three times. Existing JSON checkpoints remain loadable, and sentence-retrieval continuity remains active. See `docs/story-engine-design.md` for the research and limitations and `docs/model-evaluation.md` for the controlled local-model comparison.

## Output

Generated novels are saved to the `output/` directory as EPUB files with cover art and chapter illustrations.

## License

This project is licensed under [CC BY-NC 4.0](https://darren-static.waft.dev/license) - free to use and modify, but no commercial use without permission.
