import asyncio
import hashlib
import json
from pathlib import Path
from typing import Type

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock
from pydantic import BaseModel

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
CACHE_DIR = SCRIPT_DIR / "output" / "cache"

OPUS_MODEL = "claude-opus-4-6"
HAIKU_MODEL = "claude-haiku-4-5-20251001"


# ##################################################################
# hash input
# create a deterministic hash from input arguments for cache keying
def _hash_input(messages: list[dict], model: str, extra: str = "") -> str:
    input_str = json.dumps({"messages": messages, "model": model, "extra": extra}, sort_keys=True, default=str)
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
# extract text
# pull the text content from claude agent sdk response messages
def _extract_text(messages) -> str:
    response_text = ""
    for message in messages:
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    response_text += block.text
    return response_text.strip()


# ##################################################################
# parse json response
# handle the fact that claude sometimes wraps json in markdown code blocks
def _parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


# ##################################################################
# chat
# send a chat message to claude and get a text response, with caching
def chat(messages: list[dict[str, str]], model: str = OPUS_MODEL) -> str:
    hash_key = _hash_input(messages, model)
    cached = _load_from_cache(hash_key)
    if cached:
        return cached["output"]

    system_prompt, user_prompt = _split_messages(messages)

    async def _run():
        collected = []
        async for message in query(
            prompt=user_prompt,
            options=ClaudeAgentOptions(
                model=model,
                system_prompt=system_prompt or None,
                allowed_tools=[],
                permission_mode="bypassPermissions",
                max_turns=1,
            ),
        ):
            collected.append(message)
        return _extract_text(collected)

    result = asyncio.run(_run())
    if not result:
        raise ValueError("Claude returned empty response")
    _save_to_cache(hash_key, {"messages": messages, "model": model}, result)
    return result


# ##################################################################
# chat structured
# send a chat message and parse the response into a pydantic model
def chat_structured(messages: list[dict[str, str]], model_class: Type[BaseModel], model: str = OPUS_MODEL) -> BaseModel:
    hash_key = _hash_input(messages, model, extra=model_class.__name__)
    cached = _load_from_cache(hash_key)
    if cached:
        return model_class(**cached["output"])

    schema = json.dumps(model_class.model_json_schema(), indent=2)
    structured_messages = messages.copy()
    last_msg = structured_messages[-1]
    structured_messages[-1] = {
        "role": last_msg["role"],
        "content": last_msg["content"] + f"\n\nRespond with ONLY valid JSON matching this schema:\n{schema}\n\nReturn JSON only, no explanation.",
    }

    system_prompt, user_prompt = _split_messages(structured_messages)

    async def _run():
        collected = []
        async for message in query(
            prompt=user_prompt,
            options=ClaudeAgentOptions(
                model=model,
                system_prompt=system_prompt or None,
                allowed_tools=[],
                permission_mode="bypassPermissions",
                max_turns=1,
            ),
        ):
            collected.append(message)
        return _extract_text(collected)

    result_text = asyncio.run(_run())
    if not result_text:
        raise ValueError("Claude returned empty response")

    parsed = _parse_json_response(result_text)
    result = model_class(**parsed)
    _save_to_cache(hash_key, {"messages": messages, "model": model, "model_class": model_class.__name__}, result.model_dump())
    return result


# ##################################################################
# split messages
# separate system prompt from user content for the sdk
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
# clear cache
# remove all cached llm responses
def clear_cache() -> None:
    if CACHE_DIR.exists():
        for cache_file in CACHE_DIR.glob("*.json"):
            cache_file.unlink()
