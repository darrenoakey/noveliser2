![](banner.jpg)

Here's the README:

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

Generation is resumable -- if interrupted, you can pick up where you left off.

## Prerequisites

- Python 3.12+
- An Anthropic API key set in your environment (`ANTHROPIC_API_KEY`)

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

Covers `create`, `continue`, `list-finished`, `list-ongoing`, `test`, `test_bigger`, and `check` commands with examples for different novel sizes, custom authors, and resuming interrupted generations.

## Output

Generated novels are saved to the `output/` directory as EPUB files with cover art and chapter illustrations.