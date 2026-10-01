#!/usr/bin/env python3
"""Generate the acceptance novel after the short pilot has passed its gates.

Eight chapters and five sections is a full book without the default 100-scene run.
Images stay off through local/config.toml. Resume with the book directory argument.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from models import Character  # noqa: E402
from pipeline import write_novel  # noqa: E402
from premise import NOVEL_PREMISE, acceptance_guard  # noqa: E402
from story_validation import PremiseGuard  # noqa: E402

TITLE = "The Weight of Wonder"
STYLE = (
    "Late-medieval travelling-show prose: concrete apparatus, hands, weather, and cost. "
    "Distinct spoken voices. Do not repeat an image or sentence rhythm inside a section. "
    "No prophecy, no second real magician, no witch trial."
)


def premise_for(characters: list[Character]) -> PremiseGuard:
    protagonist = next(character.name for character in characters if character.role.value == "protagonist")
    guard = acceptance_guard(protagonist)
    allowed = tuple(part for character in characters for part in character.name.split())
    return PremiseGuard(
        protagonist=guard.protagonist,
        required_phrases=guard.required_phrases,
        forbidden=guard.forbidden,
        allowed_names=allowed,
    )


def main() -> None:
    continue_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    epub = write_novel(
        NOVEL_PREMISE,
        ROOT / "output",
        num_chapters=8,
        sections_per_chapter=5,
        author="Darren Oakey",
        title=TITLE,
        style_directive=STYLE,
        continue_novel_dir=continue_dir,
        premise_factory=premise_for,
    )
    print("novel_epub", epub, flush=True)


if __name__ == "__main__":
    main()
