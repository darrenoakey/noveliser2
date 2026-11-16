import json
import subprocess
import sys
from pathlib import Path

import pytest

from brain import _extract_json, _is_degenerate, _request_cache_key
from models import WritingStyle


def test_request_cache_identity_survives_process_restart():
    messages = [{"role": "user", "content": "Choose a precise voice."}]
    expected = _request_cache_key(messages, "WritingStyle")
    source = Path(__file__).resolve().parent
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from brain import _request_cache_key; "
        "print(_request_cache_key([{'role':'user','content':'Choose a precise voice.'}], 'WritingStyle'))"
    )
    restarted = subprocess.check_output([sys.executable, "-c", code, str(source)], text=True).strip()
    assert restarted == expected
    assert _request_cache_key(messages, "OtherSchema") != expected
    assert _request_cache_key([{"role": "user", "content": "A different voice."}], "WritingStyle") != expected


def test_actual_model_response_preserves_literal_newlines():
    source = Path(__file__).parent / "style_samples/responses/literal_newlines.txt"
    data = _extract_json(source.read_text())
    style = WritingStyle(**data)
    assert style.is_rich()
    assert "\n1. **Point of view:**" in style.revision_brief
    assert json.loads(json.dumps(data)) == data


def test_structured_decode_rejects_unsafe_controls_and_bad_structure():
    for text in ['{"text":"bad\x00control"}', '{"unclosed": "text}']:
        with pytest.raises(ValueError):
            _extract_json(text)
    with pytest.raises(TypeError, match="must be a JSON object"):
        _extract_json('["not an object"]')
    assert _extract_json('```json\n{"answer":"one\ntwo"}\n```') == {"answer": "one\ntwo"}


def test_degeneracy_check_uses_class_schema_without_deprecation():
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert _is_degenerate(WritingStyle(style_description="", tone="", voice="", pacing=""))
