"""Planning brain — delegates to agentd3 daemon subagents.

Every pipeline stage (title, plot type, themes, characters, outline, writing
style, chapter/section breakdown) runs as an agentd3 subagent conversation on
a cloud model, not a local arbiter/ollama box. `chat` returns prose, and
`chat_structured` returns a pydantic model parsed from the subagent's JSON.

Results are cached on disk so a resumed run never re-pays for a stage.
"""

from __future__ import annotations

import hashlib
import json
import re
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

from agentd3_client import create_subagent, run_to_completion

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
CACHE_DIR = SCRIPT_DIR / "output" / "cache"

# Planning needs the same reliable fiction model as prose. The broad high-tier
# route exhausted Gemini quota and stalled on its provider failover during live
# style enrichment; the explicit prose model completed the real revision calls.
PLANNING_MODEL = "claude/fable-5.2"
RETRY_MODEL = "claude/fable-5.2"


# ##################################################################
# cache path
def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{key}.json"


# ##################################################################
# load cache
def _load_cache(key: str) -> dict | None:
    path = _cache_path(key)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ##################################################################
# save cache
def _save_cache(key: str, payload: dict) -> None:
    with open(_cache_path(key), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)


# ##################################################################
# extract json
# pull the first {...} object out of the subagent's reply, tolerating any
# prose around it.
def _extract_json(text: str) -> dict:
    text = text.strip()
    # Models sometimes put literal line breaks/tabs inside long string values.
    # Decode those without altering the text; cache serialization re-escapes them.
    # Other raw controls (including NUL) are not legitimate prose and fail closed.
    if any(ord(char) < 32 and char not in "\r\n\t" for char in text):
        raise ValueError("Unexpected control character in structured model reply")
    try:
        data = json.loads(text, strict=False)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError(f"no JSON object found in subagent reply: {text[:200]}") from None
        data = json.loads(match.group(0), strict=False)
    if not isinstance(data, dict):
        raise TypeError("Structured model reply must be a JSON object")
    return data


# ##################################################################
# is degenerate
# true if a structured result has blank strings / empty collections in most
# of its required fields — i.e. the model returned a placeholder skeleton
# instead of real content.
def _is_degenerate(result: BaseModel) -> bool:
    return _model_degeneracy(result) > 0.5


# ##################################################################
# model degeneracy
# fraction of the model's own fields that are blank/empty/placeholder.
def _model_degeneracy(model: BaseModel) -> float:
    fields = type(model).model_fields
    if not fields:
        return 0.0
    blank = 0
    for name in fields:
        value = getattr(model, name, None)
        if _is_blank_value(value):
            blank += 1
    return blank / len(fields)


# ##################################################################
# is blank value
# a value counts as blank if it is an empty/placeholder string, an empty
# collection, or a nested model that is itself mostly blank.
def _is_blank_value(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip().lower()
        return text == "" or text.startswith(("not provided", "(none"))
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return True
        # list of models — degenerate if every item is mostly blank
        if all(isinstance(item, BaseModel) for item in value):
            return all(_model_degeneracy(item) > 0.5 for item in value)
        return False
    if isinstance(value, BaseModel):
        return _model_degeneracy(value) > 0.5
    return False


# ##################################################################
# fill missing
# fill missing keys with each field's default (or empty list / empty string),
# so a single omitted key does not crash the whole stage. Recurses into lists
# of nested models.
def _fill_missing(data: dict, model_class: type[BaseModel]) -> None:
    if not isinstance(data, dict):
        return
    for name, field in model_class.model_fields.items():
        if name in data:
            # recurse into nested model lists
            _fill_nested(data[name], field.annotation)
            continue
        data[name] = _default_for(field)


# ##################################################################
# fill nested
# for list[SomeModel] values, recurse so nested items also get missing keys.
def _fill_nested(value, annotation) -> None:
    if not isinstance(value, list):
        return
    item_cls = _model_in_container(annotation)
    if item_cls is None:
        return
    for item in value:
        if isinstance(item, dict):
            _fill_missing(item, item_cls)


# ##################################################################
# model in container
# unwrap a list[...] annotation to find a BaseModel subclass, if any.
def _model_in_container(annotation) -> type[BaseModel] | None:
    if getattr(annotation, "__origin__", None) is None:
        return None
    for arg in getattr(annotation, "__args__", ()):
        if isinstance(arg, type) and issubclass(arg, BaseModel):
            return arg
    return None


# ##################################################################
# default for
# produce a reasonable default for a model field.
def _default_for(field) -> object:
    if field.default is not None and field.default.__class__.__name__ != "PydanticUndefinedType":
        return field.default
    annotation = field.annotation
    origin = getattr(annotation, "__origin__", None)
    if origin is not None:  # list[...] / dict[...] / optional
        if origin is list:
            return []
        if origin is dict:
            return {}
    if annotation is str:
        return ""
    if annotation is int:
        return 0
    if annotation is float:
        return 0.0
    if annotation is bool:
        return False
    return None


# ##################################################################
# normalize enums
# the subagent may emit an enum value with different case ("Comedy" vs the
# member name "COMEDY"). Rewrite string values to the matching member name so
# pydantic validation succeeds.
def _normalize_enums(data: dict, model_class: type[BaseModel]) -> None:
    if not isinstance(data, dict):
        return
    for name, field in model_class.model_fields.items():
        if name not in data:
            continue
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            _match_enum_value(data, name, annotation)
        else:
            # list[Enum] or similar container — normalize each element
            enum_cls = _enum_in_container(annotation)
            value = data[name]
            if enum_cls is not None and isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        data[name][i] = _enum_member_value(enum_cls, item)
            # list[BaseModel] — recurse so nested enums get normalized too
            item_cls = _model_in_container(annotation)
            if item_cls is not None and isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        _normalize_enums(item, item_cls)


# ##################################################################
# match enum value
# rewrite data[key] to the enum member's value if the string matches a member
# (by name or value), case-insensitively.
def _match_enum_value(data: dict, key: str, enum_cls: type[Enum]) -> None:
    value = data[key]
    if isinstance(value, str):
        data[key] = _enum_member_value(enum_cls, value)


# ##################################################################
# enum member value
# return the enum member's value that matches the string (by name or value).
# Falls back to the first member when nothing matches, so a free-text answer
# still yields a valid model rather than crashing the stage.
def _enum_member_value(enum_cls: type[Enum], text: str):
    lowered = text.strip().lower()
    for member in enum_cls:
        if lowered == member.name.lower() or lowered == str(member.value).lower():
            return member.value
    # fuzzy: if the text contains a member's value/name (e.g. "supporting ally"
    # contains "supporting"), use that member
    for member in enum_cls:
        value = str(member.value).lower()
        if value and value in lowered:
            return member.value
    for member in enum_cls:
        name = member.name.lower()
        if len(name) > 3 and name in lowered:
            return member.value
    members = list(enum_cls)
    return members[0].value if members else text


# ##################################################################
# schema instruction
# build an explicit "use exactly these keys" instruction from the model's
# fields, so the subagent names keys correctly.
def _schema_instruction(model_class: type[BaseModel]) -> str:
    fields = model_class.model_fields
    key_list = ", ".join(f'"{name}"' for name in fields)
    lines = [
        "Respond with ONLY a single JSON object. It MUST have exactly these keys: " + key_list + ".",
    ]
    for name, field in fields.items():
        annotation = field.annotation
        type_name = getattr(annotation, "__name__", str(annotation))
        desc = (field.description or "").strip()
        # surface the allowed values for enum-typed fields (including lists of enums)
        enum_cls = annotation if isinstance(annotation, type) and issubclass(annotation, Enum) else None
        if enum_cls is None:
            enum_cls = _enum_in_container(annotation)
        if enum_cls is not None:
            allowed = ", ".join(f'"{m.value}"' for m in enum_cls)
            lines.append(f'- "{name}" ({type_name}): {desc} MUST be one of exactly these values: {allowed}.')
        elif desc:
            lines.append(f'- "{name}" ({type_name}): {desc}')
        else:
            lines.append(f'- "{name}" ({type_name})')
    lines.append("No prose, no code fences, no commentary, no extra keys — just that JSON object.")
    return "\n".join(lines)


# ##################################################################
# enum in container
# unwrap a list[...] annotation to find an Enum subclass, if any.
def _enum_in_container(annotation) -> type[Enum] | None:
    if getattr(annotation, "__origin__", None) is None:
        return None
    for arg in getattr(annotation, "__args__", ()):
        if isinstance(arg, type) and issubclass(arg, Enum):
            return arg
    return None


# ##################################################################
# chat
# run a one-off agentd3 subagent for a prose answer, with disk caching.
def chat(messages: list[dict], max_tokens: int = 4096, **_ignored) -> str:
    key = _request_cache_key(messages, "text")
    cached = _load_cache(key)
    if cached is not None:
        return cached["output"]

    system, prompt = _split_messages(messages)
    conv_id = create_subagent(system_prompt=system, title="noveliser2 planning", model=PLANNING_MODEL)
    result = run_to_completion(conv_id, prompt)

    _save_cache(key, {"messages": messages, "output": result})
    return result


def _request_cache_key(messages: list[dict], schema_name: str) -> str:
    identity = {"messages": messages, "schema": schema_name, "model": PLANNING_MODEL}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, default=str).encode()).hexdigest()
    return "plan_" + digest


# ##################################################################
# chat structured
# run a one-off agentd3 subagent and parse its reply into a pydantic model.
def chat_structured(messages: list[dict], model_class: type[BaseModel], **_ignored) -> BaseModel:
    key = _request_cache_key(messages, model_class.__name__)
    cached = _load_cache(key)
    if cached is not None:
        return model_class(**cached["output"])

    system, prompt = _split_messages(messages)
    structured_prompt = prompt + "\n\n" + _schema_instruction(model_class)
    conv_id = create_subagent(system_prompt=system, title=f"noveliser2 {model_class.__name__}", model=PLANNING_MODEL)
    result_text = run_to_completion(conv_id, structured_prompt)
    try:
        data = _extract_json(result_text)
        _normalize_enums(data, model_class)
        _fill_missing(data, model_class)
        result = model_class(**data)
        if _is_degenerate(result):
            raise ValueError("structured result has blank or placeholder content")
    except (ValueError, TypeError):
        # retry once on a stronger model with an explicit content note
        retry_prompt = structured_prompt + (
            "\n\nYour previous reply had blank or missing content. Return the SAME JSON object with "
            "every field filled with real, specific content — no empty strings, no placeholder text."
        )
        conv_id = create_subagent(
            system_prompt=system, title=f"noveliser2 {model_class.__name__} retry", model=RETRY_MODEL
        )
        result_text = run_to_completion(conv_id, retry_prompt)
        data = _extract_json(result_text)
        _normalize_enums(data, model_class)
        _fill_missing(data, model_class)
        result = model_class(**data)
        if _is_degenerate(result):
            raise ValueError("Retry returned blank or placeholder structured content")

    _save_cache(key, {"messages": messages, "output": result.model_dump()})
    return result


# ##################################################################
# split messages
# fold the message list into a single system + user prompt pair.
def _split_messages(messages: list[dict]) -> tuple[str, str]:
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
def clear_cache() -> None:
    if CACHE_DIR.exists():
        for cache_file in CACHE_DIR.glob("*.json"):
            cache_file.unlink()
