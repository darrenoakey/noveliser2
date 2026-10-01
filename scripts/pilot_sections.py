#!/usr/bin/env python3
# Real section planner and two-section prose continuation on an accepted chapter plan.
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
from models import CharactersList, ChapterPlan, WritingStyle  # noqa: E402
from break_into_sections import break_into_sections  # noqa: E402
from write_section import write_section  # noqa: E402
from retrieval_memory import RetrievalMemory  # noqa: E402

OUT = ROOT / 'output' / 'acceptance_pilot'


def main():
    cast = CharactersList(**json.loads((OUT / 'characters.json').read_text()))
    chapters = ChapterPlan(**json.loads((OUT / 'chapters.json').read_text()))
    style = WritingStyle(**json.loads((OUT / 'style.json').read_text()))
    sections = break_into_sections(chapters.chapters[0], 2, chapters.chapters, cast.characters)
    (OUT / 'sections.json').write_text(sections.model_dump_json(indent=2))
    print('validated', len(sections.sections), 'sections', flush=True)
    memory = RetrievalMemory()
    previous = ''
    for section in sections.sections:
        result = write_section(chapters.chapters[0], section, previous, memory, cast.characters,
                               style, chapters, False)
        (OUT / f'section_{section.number}.json').write_text(result.model_dump_json(indent=2))
        print('wrote', section.number, len(result.text.split()), 'words', flush=True)
        memory.ensure_section(f'ch1.s{section.number}', result.text)
        previous += '\n\n' + result.text
    print('pilot_complete', len(previous.split()), 'words', flush=True)


if __name__ == '__main__':
    main()
