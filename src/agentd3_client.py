"""Minimal client for spawning agentd3 daemon subagent conversations.

Prose sections are written by a subagent conversation rather than a one-shot
SDK completion. A subagent keeps its own growing context across the sections
it writes, so the orchestrator pays tokens only for what each individual
subagent actually needs — not for the whole accumulated novel every call.

Each subagent conversation is created with a system prompt describing the
novelist role and the craft rules, then given a short per-scene prompt. The
last assistant message is the prose.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from backend import _validate_section, read_configuration

DEFAULT_API_BASE = "http://127.0.0.1:8620"
# the prose model: Claude Fable 5.2, the frontier model for the core
# creative writing ("the real core thinking in the middle").
DEFAULT_MODEL = "claude/fable-5.2"
DEFAULT_CWD = str(Path.home() / "src" / "noveliser2")
DEFAULT_SOURCE = "noveliser2"

POLL_INTERVAL_SECONDS = 10
POLL_TIMEOUT_SECONDS = 60 * 45


class Agentd3Error(RuntimeError):
    """Raised when the daemon subagent run fails."""


_config_path: Path | None = None
_overrides: dict[str, str] = {}


def configure(
    *,
    api_base: str | None = None,
    prose_model: str | None = None,
    config_path: str | Path | None = None,
) -> None:
    """Replace agentd3-only process overrides; configure() resets to the default file.

    Persist non-secret settings in [agentd3] in local/config.toml. Explicitly
    selected files must exist; invalid files are never masked by overrides.
    Backend overrides are independent and are not changed by this function.
    """
    global _config_path, _overrides
    values = {"api_base": api_base, "prose_model": prose_model}
    overrides = _validate_section(
        "agentd3", {key: value for key, value in values.items() if value is not None}
    )
    selected_path = Path(config_path).resolve() if config_path is not None else None
    read_configuration(selected_path)
    _config_path, _overrides = selected_path, overrides


def _settings(config_path: str | Path | None = None) -> dict[str, str]:
    document = read_configuration(
        config_path if config_path is not None else _config_path
    )
    return document.get("agentd3", {}) | _overrides


# ##################################################################
# api base url
def _api_base(config_path: str | Path | None = None) -> str:
    return _settings(config_path).get("api_base", DEFAULT_API_BASE).rstrip("/")


def get_prose_model(config_path: str | Path | None = None) -> str:
    return _settings(config_path).get("prose_model", DEFAULT_MODEL)


# ##################################################################
# request
# thin json http helper over urllib so we add no third-party dependency.
def _request(
    method: str, path: str, payload: dict | None = None, timeout: int = 60
) -> dict:
    url = _api_base() + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise Agentd3Error(f"{method} {path} -> HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise Agentd3Error(
            f"{method} {path} -> connection error: {exc.reason}"
        ) from exc
    return json.loads(body) if body else {}


# ##################################################################
# create subagent
# spin up a fresh subagent conversation pinned to a model. returns its id.
def create_subagent(
    system_prompt: str,
    title: str,
    model: str | None = None,
    cwd: str = DEFAULT_CWD,
    source: str = DEFAULT_SOURCE,
    context_mode: str = "lcm",
) -> str:
    response = _request(
        "POST",
        "/v1/conversations",
        {
            "model": model if model is not None else get_prose_model(),
            "cwd": cwd,
            "source": source,
            "title": title[:200],
            "system_prompt": system_prompt,
            "tool_profile": "structured",
            "policy": "readonly",
            "context_mode": context_mode,
        },
        timeout=60,
    )
    conv_id = response.get("conversation_id") or response.get("id")
    if not conv_id:
        raise Agentd3Error(f"daemon did not return a conversation id: {response}")
    return conv_id


# ##################################################################
# post prompt
# append a user message to the subagent conversation.
def post_prompt(conv_id: str, prompt: str) -> None:
    _request(
        "POST", f"/v1/conversations/{conv_id}/messages", {"text": prompt}, timeout=60
    )


# ##################################################################
# get conversation
def get_conversation(conv_id: str) -> dict:
    return _request("GET", f"/v1/conversations/{conv_id}", timeout=60)


# ##################################################################
# get events
# pull the conversation event stream (turn/message lifecycle + text).
def get_events(conv_id: str) -> list[dict]:
    data = _request("GET", f"/v1/conversations/{conv_id}/events", timeout=60)
    return data.get("events", [])


# ##################################################################
# last assistant message
# scan the event stream for the most recent completed assistant message.
def last_assistant_message(conv_id: str) -> str:
    text = ""
    for event in get_events(conv_id):
        if event.get("type") != "message.completed":
            continue
        data = event.get("data", {})
        if data.get("role") not in (None, "", "assistant"):
            continue
        if data.get("text"):
            text = data["text"]
    return text


# ##################################################################
# turn in progress
# true while the conversation has an unfinished turn (the daemon idles at a
# completed=false 'idle' status between turns, so per-turn polling is needed).
def turn_in_progress(conv_id: str) -> bool:
    conv = get_conversation(conv_id)
    if conv.get("running"):
        return True
    events = get_events(conv_id)
    started = 0
    completed = 0
    for event in events:
        etype = event.get("type")
        if etype == "turn.started":
            started += 1
        elif etype == "turn.completed":
            completed += 1
    return started > completed


# ##################################################################
# run to completion
# post a prompt, then poll until the turn completes and return the assistant
# text.
def run_to_completion(
    conv_id: str,
    prompt: str,
    poll_interval: int = POLL_INTERVAL_SECONDS,
    timeout_seconds: int = POLL_TIMEOUT_SECONDS,
) -> str:
    post_prompt(conv_id, prompt)
    deadline = time.monotonic() + timeout_seconds
    settle_deadline: float | None = None
    while time.monotonic() < deadline:
        if turn_in_progress(conv_id):
            settle_deadline = None
            time.sleep(poll_interval)
            continue
        text = last_assistant_message(conv_id)
        if text.strip():
            return text
        # The turn isn't marked in-progress, but a message.completed for it may
        # not have settled yet (the status lags behind the delta stream). Hold a
        # short settle window before concluding the turn produced no text.
        if settle_deadline is None:
            settle_deadline = time.monotonic() + 45
        if time.monotonic() < settle_deadline:
            time.sleep(3)
            continue
        raise Agentd3Error(
            f"subagent {conv_id} finished its turn with no assistant text"
        )
    raise Agentd3Error(f"subagent {conv_id} did not complete within {timeout_seconds}s")
