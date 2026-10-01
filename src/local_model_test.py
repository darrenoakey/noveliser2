from pathlib import Path
import urllib.error
import urllib.request

from pydantic import BaseModel
import pytest

from local_model import load_local_model_config, local_chat


class CoinResult(BaseModel):
    coin: str
    consequence: str


def test_local_chat_returns_real_structured_story_beat() -> None:
    config = {"ollama_url": "http://10.0.0.42:11434"}
    try:
        with urllib.request.urlopen(config["ollama_url"] + "/api/tags", timeout=3) as response:
            assert response.status == 200
    except (OSError, urllib.error.URLError) as error:
        pytest.skip(f"boringstack Ollama is unreachable: {error}")
    content = local_chat(
        [{"role": "user", "content": "Return a copper coin and a consequence of stealing it."}],
        "qwen3:8b", config, 110, schema=CoinResult,
    )
    beat = CoinResult.model_validate_json(content)
    assert beat.coin.strip() and beat.consequence.strip()


def test_config_is_explicit_and_fails_closed(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    assert load_local_model_config(config_path) is None
    config_path.write_text('text_backend = "ollama"\nollama_url = "http://localhost:11434"\n')
    try:
        load_local_model_config(config_path)
    except ValueError as error:
        assert "planning_model" in str(error)
    else:
        raise AssertionError("Incomplete configured local backend must not be silently ignored")
    config_path.write_text('text_backend = "typo"\n')
    with pytest.raises(ValueError, match="Unsupported configured text backend"):
        load_local_model_config(config_path)
