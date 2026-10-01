#!/usr/bin/env python3
# Run real planning and two sections before permitting the expensive full novel.
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from create_characters import create_characters  # noqa: E402
from determine_plot_type import determine_plot_type  # noqa: E402
from select_themes import select_themes  # noqa: E402
from create_outline import create_outline  # noqa: E402
from enhance_outline import enhance_outline  # noqa: E402
from define_writing_style import define_writing_style  # noqa: E402
from break_into_chapters import break_into_chapters  # noqa: E402
from break_into_sections import break_into_sections  # noqa: E402
from write_section import write_section  # noqa: E402
from retrieval_memory import RetrievalMemory  # noqa: E402
from create_schedule_contract import create_schedule_contract  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from premise import PREMISE, acceptance_guard  # noqa: E402

OUT = ROOT / "output" / "acceptance_pilot"
OUT.mkdir(parents=True, exist_ok=True)


def save(name, value):
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(value.model_dump() if hasattr(value, "model_dump") else value,
                               indent=2, ensure_ascii=False))
    print('saved', path, flush=True)


def main():
    plot = determine_plot_type(PREMISE)
    save('plot', plot)
    themes = select_themes(PREMISE, plot.plot_type.value)
    save('themes', themes)
    values = [t.value for t in themes.themes]
    cast = create_characters(PREMISE, plot.plot_type.value, values)
    save('characters', cast)
    protagonist = next(c.name for c in cast.characters if c.role.value == "protagonist")
    guard = acceptance_guard(protagonist)
    outline = create_outline(PREMISE, plot.plot_type.value, values, cast.characters, 3, 2, guard)
    save('outline', outline)
    enhanced = enhance_outline(outline, guard)
    save('enhanced', enhanced)
    style = define_writing_style(enhanced.outline, values)
    save('style', style)
    schedule = create_schedule_contract(enhanced, cast.characters, 3, guard)
    save('schedule', schedule)
    chapters = break_into_chapters(enhanced, cast.characters, values, plot.plot_type.value, 3,
                                   schedule, guard)
    save('chapters', chapters)
    sections = break_into_sections(chapters.chapters[0], 2, chapters.chapters, cast.characters)
    save('sections', sections)
    memory = RetrievalMemory()
    previous = ''
    for section in sections.sections:
        result = write_section(chapters.chapters[0], section, previous, memory, cast.characters,
                               style, chapters, False)
        save(f'section_{section.number}', result)
        memory.ensure_section(f'ch1.s{section.number}', result.text)
        previous += '\n\n' + result.text
    print('pilot_complete', sum(len(json.loads((OUT / f'section_{n}.json').read_text())['text'].split())
                                for n in (1, 2)), flush=True)


if __name__ == '__main__':
    main()
