import json
import os
from pathlib import Path
import subprocess
import sys


BACKEND_CONFIGURATION_NAMES = (
    "NOVELISER2_BACKEND",
    "NOVELISER2_ARBITER_HIGH_MODEL",
    "NOVELISER2_ARBITER_LOW_MODEL",
)


def run_backend_query(
    tmp_path: Path, expression: str, configuration: dict[str, str]
) -> object:
    process_environment = os.environ.copy()
    for name in BACKEND_CONFIGURATION_NAMES:
        process_environment.pop(name, None)
    process_environment.update(configuration)
    source_directory = Path(__file__).resolve().parent
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, sys; "
                "sys.path.insert(0, sys.argv[1]); "
                "from backend import get_arbiter_text_model, get_backend; "
                f"print(json.dumps({expression}))"
            ),
            str(source_directory),
        ],
        cwd=tmp_path,
        env=process_environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_get_backend_defaults_to_sdk_in_clean_process(tmp_path: Path) -> None:
    assert run_backend_query(tmp_path, "get_backend()", {}) == "sdk"


def test_get_arbiter_text_model_uses_process_configuration(tmp_path: Path) -> None:
    models = run_backend_query(
        tmp_path,
        "[get_arbiter_text_model('opus'), get_arbiter_text_model('haiku')]",
        {"NOVELISER2_ARBITER_HIGH_MODEL": "qwen3.6-27b"},
    )
    assert models == ["qwen3.6-27b", "qwen3.6-27b"]
