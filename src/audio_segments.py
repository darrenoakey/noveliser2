"""Speaker-labeled audio segments — taken from the model's own tagged output.

The prose subagent emits every line tagged with its speaker (NARRATOR or a
character name). This module assembles those generated tags into the
per-chapter audio JSON — so speaker attribution comes from generation, not
from post-hoc parsing of finished prose.
"""

from __future__ import annotations

import json
from pathlib import Path

NARRATOR = "narrator"


# ##################################################################
# segments from lines
# normalise the model's tagged lines into the audio shape, lowercasing the
# reserved narrator tag.
def segments_from_lines(lines: list[dict]) -> list[dict]:
    segments = []
    for line in lines:
        speaker = (line.get("speaker") or "").strip()
        text = (line.get("text") or "").strip()
        if not text:
            continue
        if speaker.upper() == "NARRATOR":
            speaker = NARRATOR
        segments.append({"speaker": speaker, "text": text})
    return segments


# ##################################################################
# write chapter audio
# produce one audio segment file per chapter from the generated tagged lines.
def write_chapter_audio(novel_dir: Path, chapter_number: int, chapter_lines: list[dict]) -> Path:
    segments = segments_from_lines(chapter_lines)
    audio_path = novel_dir / f"audio_chapter_{chapter_number}.json"
    with open(audio_path, "w", encoding="utf-8") as fh:
        json.dump(segments, fh, indent=2, ensure_ascii=False)
    return audio_path
