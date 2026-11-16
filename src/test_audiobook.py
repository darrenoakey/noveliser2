"""Real filesystem/ffmpeg and remote-arbiter tests, without service substitutes."""

import hashlib
import json
import time
from pathlib import Path

import pytest

from audiobook import (
    AudiobookPending,
    NarrationChapter,
    _chapters,
    _settings,
    _synthesis_capacity,
    _wav_info,
    clean_narration,
    export_audiobook,
    export_narration_script,
    split_narration,
)


def test_three_job_window_capacity():
    assert _synthesis_capacity([]) == 3
    assert _synthesis_capacity(['first']) == 2
    assert _synthesis_capacity(['first', 'second']) == 1
    assert _synthesis_capacity(['first', 'second', 'third']) == 0
    assert _synthesis_capacity(['first', 'second', 'third', 'legacy']) == 0


def test_clean_narration_preserves_story_and_names():
    source = '# Chapter One\r\n\r\n[SFX: a distant bell]\n**Mára** said, “Don’t touch it.”\n\n*Ash fell.*\n\n***\n\n[Pause for five seconds]\nThe end.'
    assert clean_narration(source) == 'Chapter One\n\nMára said, “Don’t touch it.”\n\nAsh fell.\n\nThe end.'
    assert clean_narration('The inscription read [never return].') == 'The inscription read [never return].'
    assert clean_narration('[Never return]') == '[Never return]'


def test_ambiguous_inline_directions_fail_closed():
    with pytest.raises(ValueError, match="Inline production"):
        clean_narration('She said [whisper] “Come here.”')
    with pytest.raises(ValueError, match="Empty"):
        clean_narration('[SFX: bell]')
    with pytest.raises(TypeError):
        clean_narration(None)


def test_chunking_does_not_drop_any_word_or_punctuation():
    text = ('Mára’s brother—Éolan—had said, “No.”\n\nBut the bell rang; again, and again! ' * 1000).strip()
    chunks = split_narration(text)
    assert all(0 < len(chunk) <= 420 for chunk in chunks)
    assert ' '.join(chunks) == ' '.join(text.split())
    assert sum(len(c.split()) for c in chunks) == len(text.split())
    assert chunks[-1].endswith('again!')


@pytest.mark.parametrize('limit', [0, 39, 421, 1000])
def test_unsafe_chunk_limit_rejected(limit):
    with pytest.raises(ValueError):
        split_narration('Words.', limit)


def test_unpronounceable_token_is_not_silently_truncated():
    with pytest.raises(ValueError, match='overlong'):
        split_narration('x' * 421)
    with pytest.raises(ValueError):
        split_narration(' ')


def test_script_export_and_chapter_validation(tmp_path):
    chapters = [NarrationChapter('The Bell', 'Mára listened.\n\n[Pause]\nIt rang.'),
                {'title': 'The Answer', 'text': 'Nobody answered.'}]
    path = export_narration_script(chapters, 'Winter: Bells / Return', tmp_path)
    assert path.parent == tmp_path
    assert path.read_text() == 'Winter: Bells / Return\n\nThe Bell\n\nMára listened.\n\nIt rang.\n\nThe Answer\n\nNobody answered.\n'
    with pytest.raises(ValueError):
        _chapters([])
    with pytest.raises(ValueError):
        _chapters([{'title': '', 'text': 'a'}])


def test_config_is_explicit_and_never_accepts_inline_credentials(tmp_path):
    path = tmp_path / 'config.toml'
    path.write_text('[audiobook]\nvoice="bf_emma"\nspeed=0.98\n')
    assert _settings(path)['voice'] == 'bf_emma'
    for field in ['api_key="secret"', 'speed=0.1', 'base_url="http://localhost:8400"',
                  'base_url="http://user:secret@example.org"', 'token_service="arbiter"']:
        path.write_text('[audiobook]\n' + field + '\n')
        with pytest.raises(ValueError):
            _settings(path)


def test_real_remote_audiobook_and_restart_resume():
    """Two real chapters, AAC decode, metadata, and job-ID reuse on restart.

    Test artifacts persist under output/testing so terminating/restarting pytest
    resumes the actual remote work rather than duplicating queued jobs.
    """
    root = Path(__file__).resolve().parent.parent / 'output' / 'testing' / 'audiobook'
    root.mkdir(parents=True, exist_ok=True)
    config = root / 'config.toml'
    config.write_text('[audiobook]\nvoice="bf_emma"\nspeed=0.98\n')
    chapters = [
        {'title': 'The Bell', 'text': 'Mara found the bell beneath the snow. It had no clapper. Nevertheless, when she touched the rim, something under the mountain answered.'},
        {'title': 'The Promise', 'text': '“Not yet,” Mara told it. “My brother is still down there.” She wrapped the bell in her coat and began the long descent.'},
    ]
    deadline = time.monotonic() + 180
    seen = set()
    while True:
        try:
            result = export_audiobook(chapters, 'Winter Bells Integration', root,
                                     author='Noveliser integration', config_path=config)
            break
        except AudiobookPending as pending:
            seen.add(pending.job_id)
            assert pending.job_id
            if time.monotonic() > deadline:
                pytest.fail(f'Real remote TTS not completed within 180s; persisted job {pending.job_id}')
            time.sleep(2)
    report = json.loads((root / 'Winter Bells Integration.audiobook.json').read_text())
    assert report['engine'] == 'remote arbiter tts-kokoro'
    assert report['voice'] == 'bf_emma'
    assert report['chunks'] >= 2
    assert len(report['chapters']) == 2
    assert report['duration_seconds'] > 10
    assert report['audio_sha256'] == hashlib.sha256(result.read_bytes()).hexdigest()
    manifests = list((root / 'audiobook-work').glob('*/manifest.json'))
    assert len(manifests) == 1
    work = manifests[0].parent
    job_files = sorted(work.glob('batch-*.json'))
    original_jobs = [p.read_bytes() for p in job_files]
    wavs = sorted(work.glob('[0-9]*.wav'))
    assert len(wavs) == report['chunks']
    assert all(_wav_info(p)[3] > 0 for p in wavs)
    # New invocation uses disk state only, with no in-memory session dependency.
    second = export_audiobook(chapters, 'Winter Bells Integration', root,
                              author='Noveliser integration', config_path=config)
    assert result == second
    assert [p.read_bytes() for p in job_files] == original_jobs
    assert seen.issubset({json.loads(p.read_text())['job_id'] for p in job_files})
