"""Real tests for brain.py's validated cache (#95). No mocks — the live tests
call the real backend and skip cleanly when it is unreachable. Prompts carry a
per-run uuid so no cache layer (including the model server's own) can ever
serve a stale answer across runs.
"""

import json
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import brain  # noqa: E402

_POISON = "1.  **Analyze User Input:**\n   - **POV/Tense:** third person past."


def _backend_available() -> bool:
    try:
        return bool(brain.chat(
            [{"role": "user", "content": f"[{uuid.uuid4().hex[:8]}] Reply with the single word: ok"}],
            max_tokens=16,
        ))
    except Exception:
        return False


def _cache_path_for(messages, max_tokens):
    selector = f"tier:{brain.TIER.value}"
    key = brain._hash_input(messages, selector, extra=f"max_tokens:{max_tokens}")
    return brain.CACHE_DIR / f"{key}.json"


def test_poisoned_cache_entry_is_regenerated_live():
    if not _backend_available():
        pytest.skip("model backend unreachable")
    nonce = uuid.uuid4().hex
    messages = [{"role": "user", "content": f"[{nonce}] Write one short sentence about a lighthouse."}]

    first = brain.chat(messages, max_tokens=64)
    path = _cache_path_for(messages, 64)
    assert path.exists(), "live response must be cached"

    # poison the cache the way a bad earlier run would have
    data = json.loads(path.read_text())
    data["output"] = _POISON
    path.write_text(json.dumps(data))

    # without a validator the poison is served (documents the old behavior)
    assert brain.chat(messages, max_tokens=64) == _POISON

    # with a validator the poison is treated as a miss and regenerated
    validate = lambda t: "analyze user input" not in t.lower()  # noqa: E731
    healed = brain.chat(messages, max_tokens=64, validate=validate)
    assert healed != _POISON
    assert "analyze user input" not in healed.lower()

    # and the healed response overwrote the poisoned cache entry
    stored = json.loads(path.read_text())["output"]
    assert stored == healed
    assert first  # first response existed (sanity)


def test_invalid_fresh_response_is_not_cached():
    if not _backend_available():
        pytest.skip("model backend unreachable")
    nonce = uuid.uuid4().hex
    messages = [{"role": "user", "content": f"[{nonce}] Write one short sentence about a river."}]

    reject_all = lambda t: False  # noqa: E731
    out = brain.chat(messages, max_tokens=64, validate=reject_all)
    assert out  # caller still receives the response (its own guards handle it)
    assert not _cache_path_for(messages, 64).exists(), (
        "a response the validator rejected must never be written to the cache"
    )
