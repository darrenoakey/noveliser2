#!/usr/bin/env python3
"""Resume from the premise-valid outline and plan exactly three chapters."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from models import CharactersList, EnhancedOutline, PlotType, ThemeSelection  # noqa: E402
from create_schedule_contract import create_schedule_contract  # noqa: E402
from break_into_chapters import break_into_chapters  # noqa: E402
from premise import acceptance_guard  # noqa: E402
from story_validation import validate_premise  # noqa: E402

_ROLE_NAME = re.compile(r"\b(Engineer|Lord|Lady|Duke|Captain)\s+([A-Z][a-z]{2,})\b")


def anonymize_invented_roles(text: str, allowed: set[str]) -> str:
    """Replace titled names outside the cast with an unnamed role."""
    invented: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(2)
        if name.lower() in allowed:
            return match.group(0)
        invented.append(name)
        return "the " + match.group(1).lower()

    updated = _ROLE_NAME.sub(replace, text)
    for name in invented:
        updated = re.sub(rf"\b{name}\b", "the engineer", updated)
    return updated


def main() -> None:
    pilot = ROOT / "output" / "acceptance_pilot"
    cast = CharactersList(**json.loads((pilot / "characters.json").read_text()))
    plot = PlotType(**json.loads((pilot / "plot.json").read_text()))
    themes = ThemeSelection(**json.loads((pilot / "themes.json").read_text()))
    allowed = {part.lower() for character in cast.characters for part in character.name.split()}
    protagonist = next(c.name for c in cast.characters if c.role.value == "protagonist")
    guard = acceptance_guard(protagonist)

    outline = anonymize_invented_roles(json.loads((pilot / "outline.json").read_text()), allowed)
    enhanced_raw = json.loads((pilot / "enhanced.json").read_text())
    enhanced_raw["outline"] = anonymize_invented_roles(enhanced_raw["outline"], allowed)
    outline_issues = validate_premise(outline, guard)
    enhanced_issues = validate_premise(enhanced_raw["outline"], guard)
    if outline_issues or enhanced_issues:
        raise SystemExit(f"saved outline still violates premise: {outline_issues + enhanced_issues}")
    (pilot / "outline.json").write_text(json.dumps(outline, indent=2, ensure_ascii=False))
    enhanced = EnhancedOutline(**enhanced_raw)
    (pilot / "enhanced.json").write_text(enhanced.model_dump_json(indent=2))
    print("reusing premise-valid outline", flush=True)

    schedule = create_schedule_contract(enhanced, cast.characters, 3, guard)
    (pilot / "schedule.json").write_text(schedule.model_dump_json(indent=2))
    print("frozen schedule", len(schedule.obligations), "obligations", flush=True)
    result = break_into_chapters(
        enhanced, cast.characters, [t.value for t in themes.themes], plot.plot_type.value, 3, schedule, guard,
    )
    (pilot / "chapters.json").write_text(result.model_dump_json(indent=2))
    print("validated", len(result.chapters), "chapters", flush=True)


if __name__ == "__main__":
    main()
