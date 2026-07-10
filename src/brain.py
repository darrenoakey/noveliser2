import asyncio
import hashlib
import json
from pathlib import Path
from typing import Type

from daz_agent_sdk import agent, Tier
from pydantic import BaseModel

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
CACHE_DIR = SCRIPT_DIR / "output" / "cache"

# Default tier for every cheap/structural stage (title, outline, characters,
# section planning, style, etc.). Kept on the fast local model for cost.
TIER = Tier.FREE_FAST

# Escalated tier for reader-facing long-form PROSE generation only
# (write_section's prose call passes tier=PROSE_TIER explicitly). FREE_THINKING
# routes to the same remote boringstack model in reasoning mode — a genuinely
# stronger tier for prose quality that stays free/local, so it adds no cloud
# cost and no local-OOM risk. It is the strongest tier actually mapped in
# ~/.daz-agent-sdk/config.yaml (HIGH/MEDIUM/LOW/VERY_HIGH are unmapped here);
# every other stage stays on TIER (FREE_FAST).
PROSE_TIER = Tier.FREE_THINKING


def _hash_input(messages: list[dict], selector: str, extra: str = "") -> str:
    input_str = json.dumps({"messages": messages, "selector": selector, "extra": extra}, sort_keys=True, default=str)
    return hashlib.sha256(input_str.encode()).hexdigest()


def _load_from_cache(hash_key: str) -> dict | None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{hash_key}.json"
    if cache_path.exists():
        with open(cache_path, "r") as f:
            return json.load(f)
    return None


def _save_to_cache(hash_key: str, inputs: dict, output) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{hash_key}.json"
    cache_data = {"inputs": inputs, "output": output}
    with open(cache_path, "w") as f:
        json.dump(cache_data, f, indent=2, default=str)


def _split_messages(messages: list[dict[str, str]]) -> tuple[str, str]:
    system_parts = []
    user_parts = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_parts.append(content)
        elif role == "user":
            user_parts.append(content)
        elif role == "assistant":
            user_parts.append(f"[Previous response: {content}]")
    return "\n\n".join(system_parts), "\n\n".join(user_parts)


def chat(messages: list[dict[str, str]], max_tokens: int = 4096, tier: Tier = TIER) -> str:
    selector = f"tier:{tier.value}"
    hash_key = _hash_input(messages, selector, extra=f"max_tokens:{max_tokens}")
    cached = _load_from_cache(hash_key)
    if cached:
        return cached["output"]

    system_prompt, user_prompt = _split_messages(messages)

    async def _run() -> str:
        response = await agent.ask(user_prompt, tier=tier, system=system_prompt or None)
        return response.text

    result = asyncio.run(_run())
    if not result:
        raise ValueError("Agent returned empty response")

    cache_inputs = {"messages": messages, "tier": tier.value, "max_tokens": max_tokens}
    _save_to_cache(hash_key, cache_inputs, result)
    return result


def chat_structured(messages: list[dict[str, str]], model_class: Type[BaseModel], tier: Tier = TIER) -> BaseModel:
    selector = f"tier:{tier.value}"
    hash_key = _hash_input(messages, selector, extra=model_class.__name__)
    cached = _load_from_cache(hash_key)
    if cached:
        return model_class(**cached["output"])

    system_prompt, user_prompt = _split_messages(messages)

    async def _run() -> BaseModel:
        response = await agent.ask(
            user_prompt,
            tier=tier,
            system=system_prompt or None,
            schema=model_class,
        )
        return response.parsed  # type: ignore[union-attr]

    result = asyncio.run(_run())
    if result is None:
        raise ValueError("Agent returned empty response")

    cache_inputs = {"messages": messages, "tier": tier.value, "model_class": model_class.__name__}
    _save_to_cache(hash_key, cache_inputs, result.model_dump())
    return result


def clear_cache() -> None:
    if CACHE_DIR.exists():
        for cache_file in CACHE_DIR.glob("*.json"):
            cache_file.unlink()
