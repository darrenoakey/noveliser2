import asyncio
import hashlib
import json
from pathlib import Path
from typing import Type

from agent_sdk import agent, Tier
from pydantic import BaseModel

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
CACHE_DIR = SCRIPT_DIR / "output" / "cache"


# ##################################################################
# hash input
# create a deterministic hash from input arguments for cache keying
def _hash_input(messages: list[dict], tier: Tier, extra: str = "") -> str:
    input_str = json.dumps({"messages": messages, "tier": tier.value, "extra": extra}, sort_keys=True, default=str)
    return hashlib.sha256(input_str.encode()).hexdigest()


# ##################################################################
# load from cache
# retrieve a previously cached llm response if it exists
def _load_from_cache(hash_key: str) -> dict | None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{hash_key}.json"
    if cache_path.exists():
        with open(cache_path, "r") as f:
            return json.load(f)
    return None


# ##################################################################
# save to cache
# persist an llm response for future reuse
def _save_to_cache(hash_key: str, inputs: dict, output) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{hash_key}.json"
    cache_data = {"inputs": inputs, "output": output}
    with open(cache_path, "w") as f:
        json.dump(cache_data, f, indent=2, default=str)


# ##################################################################
# split messages
# separate system prompt from user content for agent.ask()
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


# ##################################################################
# chat
# send a chat message and get a text response, with caching
def chat(messages: list[dict[str, str]], model: str = "opus") -> str:
    tier = Tier.LOW if model == "haiku" else Tier.HIGH
    hash_key = _hash_input(messages, tier)
    cached = _load_from_cache(hash_key)
    if cached:
        return cached["output"]

    system_prompt, user_prompt = _split_messages(messages)

    async def _run() -> str:
        response = await agent.ask(
            user_prompt,
            tier=tier,
            system=system_prompt or None,
        )
        return response.text

    result = asyncio.run(_run())
    if not result:
        raise ValueError("Agent returned empty response")
    _save_to_cache(hash_key, {"messages": messages, "tier": tier.value}, result)
    return result


# ##################################################################
# chat structured
# send a chat message and parse the response into a pydantic model
def chat_structured(messages: list[dict[str, str]], model_class: Type[BaseModel], model: str = "opus") -> BaseModel:
    tier = Tier.LOW if model == "haiku" else Tier.HIGH
    hash_key = _hash_input(messages, tier, extra=model_class.__name__)
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
        return response.data  # type: ignore[union-attr]

    result = asyncio.run(_run())
    if result is None:
        raise ValueError("Agent returned empty response")
    _save_to_cache(
        hash_key,
        {"messages": messages, "tier": tier.value, "model_class": model_class.__name__},
        result.model_dump(),
    )
    return result


# ##################################################################
# clear cache
# remove all cached llm responses
def clear_cache() -> None:
    if CACHE_DIR.exists():
        for cache_file in CACHE_DIR.glob("*.json"):
            cache_file.unlink()
