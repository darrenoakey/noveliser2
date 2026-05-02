from backend import (
    SDK_BACKEND,
    get_arbiter_text_model,
    get_backend,
)


def test_get_backend_defaults_to_sdk(monkeypatch):
    monkeypatch.delenv("NOVELISER2_BACKEND", raising=False)
    assert get_backend() == SDK_BACKEND


def test_get_arbiter_text_model_falls_back_to_high_model(monkeypatch):
    monkeypatch.setenv("NOVELISER2_ARBITER_HIGH_MODEL", "qwen3.6-27b")
    monkeypatch.delenv("NOVELISER2_ARBITER_LOW_MODEL", raising=False)
    assert get_arbiter_text_model("opus") == "qwen3.6-27b"
    assert get_arbiter_text_model("haiku") == "qwen3.6-27b"
