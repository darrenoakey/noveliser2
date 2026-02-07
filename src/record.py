import json
from pathlib import Path
from typing import Any

from colorama import Fore, Style
from pydantic import BaseModel

_novel_dir: Path | None = None
_continue_mode: bool = False


# ##################################################################
# reset novel dir
# clear global state for a new novel generation run
def reset_novel_dir() -> None:
    global _novel_dir, _continue_mode
    _novel_dir = None
    _continue_mode = False


# ##################################################################
# set continue mode
# enable or disable resume-from-checkpoint behavior
def set_continue_mode(enabled: bool = True) -> None:
    global _continue_mode
    _continue_mode = enabled


# ##################################################################
# set novel dir
# explicitly set the novel output directory for continue mode
def set_novel_dir(novel_dir: Path) -> None:
    global _novel_dir
    _novel_dir = novel_dir


# ##################################################################
# get novel dir
# return the current novel directory, or None if not yet set
def get_novel_dir() -> Path | None:
    return _novel_dir


# ##################################################################
# to json data
# convert any result (pydantic model, dict, etc) to json-serializable form
def _to_json_data(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump()
    if hasattr(data, "__dict__"):
        return data.__dict__
    return data


# ##################################################################
# format for display
# create a short human-readable summary of a pipeline step result
def _format_for_display(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, BaseModel):
        if hasattr(result, "epub_path"):
            return "EPUB created"
        if hasattr(result, "title"):
            return f"'{result.title}'"
        if hasattr(result, "plot_type"):
            pt = result.plot_type
            return pt.value if hasattr(pt, "value") else str(pt)
        if hasattr(result, "themes"):
            themes = [t.value if hasattr(t, "value") else str(t) for t in result.themes]
            return ", ".join(themes[:3])
        if hasattr(result, "characters"):
            return f"{len(result.characters)} characters"
        if hasattr(result, "chapters"):
            return f"{len(result.chapters)} chapters"
        if hasattr(result, "sections"):
            return f"{len(result.sections)} sections"
    if isinstance(result, str):
        return f"'{result[:60]}...'" if len(result) > 60 else f"'{result}'"
    if isinstance(result, list):
        return f"{len(result)} items"
    if isinstance(result, dict):
        return f"{len(result)} keys"
    s = str(result)
    return s[:60] + "..." if len(s) > 60 else s


# ##################################################################
# clean title for path
# make a title safe for use as a directory name
def clean_title_for_path(title: str) -> str:
    clean = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
    return clean.replace(" ", "_")


# ##################################################################
# resolve novel dir
# determine the novel directory from a title, creating it if needed
def resolve_novel_dir(title: str, base_dir: Path) -> Path:
    global _novel_dir
    if _novel_dir is not None:
        return _novel_dir
    clean = clean_title_for_path(title)
    novel_dir = base_dir / clean
    novel_dir.mkdir(parents=True, exist_ok=True)
    _novel_dir = novel_dir
    return novel_dir


# ##################################################################
# step file name
# derive a json filename from a step description
def _step_file_name(step_description: str) -> str:
    name = step_description.lower()
    for prefix in ("generate ", "determine ", "create ", "select ", "define ", "add ", "break ", "write "):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name.replace(" ", "_") + ".json"


# ##################################################################
# record
# execute and record a pipeline step; in continue mode, skip if already done
def record(step_description: str, generator_fn, novel_dir: Path) -> Any:
    global _continue_mode

    novel_dir.mkdir(parents=True, exist_ok=True)
    file_name = _step_file_name(step_description)
    file_path = novel_dir / file_name

    if _continue_mode and file_path.exists():
        print(f"\n{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}  Skipping: {step_description} (already completed){Style.RESET_ALL}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"\n{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}  {step_description}...{Style.RESET_ALL}")

    from metadata import update_metadata_step
    update_metadata_step(novel_dir, step_description, completed=False)

    result = generator_fn()

    display = _format_for_display(result)
    print(f"{Fore.GREEN}  Result: {display}{Style.RESET_ALL}")

    json_data = _to_json_data(result)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)

    print(f"{Fore.BLUE}   Saved to: {file_path.name}{Style.RESET_ALL}")

    update_metadata_step(novel_dir, step_description, completed=True)

    return result
