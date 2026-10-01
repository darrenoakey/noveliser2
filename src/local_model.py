import json
from pathlib import Path
import tomllib
import urllib.request

from pydantic import BaseModel

CONFIG_PATH = Path(__file__).resolve().parent.parent / "local" / "config.toml"


# ##################################################################
# load local model configuration
# explicit machine-local configuration, never silently switch a configured model

def load_local_model_config(path: Path = CONFIG_PATH) -> dict | None:
    if not path.exists():
        return None
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    backend = config.get("text_backend", "sdk")
    if backend == "sdk":
        return None
    if backend != "ollama":
        raise ValueError(f"Unsupported configured text backend {backend!r} in {path}")
    for key in ("ollama_url", "planning_model", "prose_model"):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError(f"Local text backend requires {key} in {path}")
    return config


# ##################################################################
# request local model
# use an existing remote Ollama runtime for a single planning or prose generation

def local_chat(messages: list[dict[str, str]], model: str, config: dict, max_tokens: int,
               schema: type[BaseModel] | None = None, purpose: str = "planning") -> str:
    temperature = 0.7 if purpose == "prose" else 0.35
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": temperature, "num_ctx": 16384, "num_predict": max_tokens},
    }
    if schema is not None:
        payload["format"] = schema.model_json_schema()
    request = urllib.request.Request(
        config["ollama_url"].rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        output = json.load(response)
    text = output["message"]["content"]
    if not text.strip():
        raise ValueError(f"Ollama returned empty {purpose} text for {model}")
    return text
