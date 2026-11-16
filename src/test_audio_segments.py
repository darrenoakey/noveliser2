"""Unit tests for speaker-labeled audio segments from generated tags."""

import json

from audio_segments import NARRATOR, segments_from_lines, write_chapter_audio


# ##################################################################
# narrator tag is lowercased
def test_narrator_tag_lowercased():
    segments = segments_from_lines([{"speaker": "NARRATOR", "text": "The hall was silent."}])
    assert segments == [{"speaker": NARRATOR, "text": "The hall was silent."}]


# ##################################################################
# character speakers pass through
def test_character_speakers_preserved():
    lines = [
        {"speaker": "NARRATOR", "text": "Elena stopped."},
        {"speaker": "Elena", "text": "Are you coming?"},
        {"speaker": "Marcus", "text": "In a minute."},
    ]
    segments = segments_from_lines(lines)
    assert [s["speaker"] for s in segments] == [NARRATOR, "Elena", "Marcus"]
    assert segments[1]["text"] == "Are you coming?"


# ##################################################################
# blank lines dropped
def test_blank_lines_dropped():
    segments = segments_from_lines(
        [{"speaker": "Elena", "text": "  "}, {"speaker": "Elena", "text": "Hi"}]
    )
    assert len(segments) == 1
    assert segments[0]["text"] == "Hi"


# ##################################################################
# write chapter audio produces a json file
def test_write_chapter_audio(tmp_path):
    lines = [
        {"speaker": "NARRATOR", "text": "Elena smiled."},
        {"speaker": "Elena", "text": "Stay."},
    ]
    path = write_chapter_audio(tmp_path, 1, lines)
    assert path.exists()
    data = json.loads(path.read_text())
    assert isinstance(data, list)
    assert any(seg["speaker"] == "Elena" for seg in data)
    assert any(seg["speaker"] == NARRATOR for seg in data)
