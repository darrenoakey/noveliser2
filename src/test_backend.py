"""Configuration integration tests using real TOML files and fresh interpreters."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SOURCE_DIRECTORY = Path(__file__).resolve().parent
BACKEND_CONFIGURATION_NAMES = (
    "NOVELISER2_BACKEND",
    "NOVELISER2_ARBITER_BASE_URL",
    "NOVELISER2_ARBITER_HIGH_MODEL",
    "NOVELISER2_ARBITER_LOW_MODEL",
    "NOVELISER2_SKIP_IMAGES",
    "NOVELISER2_AGENTD3_API",
    "NOVELISER2_PROSE_MODEL",
)


def write_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "local" / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def run_backend_process(
    tmp_path: Path,
    expression: str,
    config_path: Path | None = None,
    *,
    setup: str = "",
    environment: dict[str, str] | None = None,
    source_directory: Path = SOURCE_DIRECTORY,
) -> subprocess.CompletedProcess:
    process_environment = os.environ.copy()
    for name in BACKEND_CONFIGURATION_NAMES:
        process_environment.pop(name, None)
    process_environment.update(environment or {})
    script = (
        "import json, sys; from pathlib import Path; "
        "sys.path.insert(0, sys.argv[1]); "
        "import backend; import agentd3_client as client; "
        "from backend import get_arbiter_text_model, get_backend; "
    )
    if config_path is not None:
        script += "backend.configure(config_path=sys.argv[2]); client.configure(config_path=sys.argv[2]); "
    script += setup + f"print(json.dumps({expression}))"
    return subprocess.run(
        [sys.executable, "-c", script, str(source_directory), str(config_path or "")],
        cwd=tmp_path,
        env=process_environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )


def run_backend_query(
    tmp_path: Path, expression: str, config_path: Path | None = None, **kwargs
) -> object:
    completed = run_backend_process(tmp_path, expression, config_path, **kwargs)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def isolated_project(tmp_path: Path) -> Path:
    source = tmp_path / "project" / "src"
    source.mkdir(parents=True)
    for name in ("backend.py", "agentd3_client.py"):
        shutil.copyfile(SOURCE_DIRECTORY / name, source / name)
    return source


def test_get_backend_defaults_to_sdk_in_clean_process(tmp_path: Path) -> None:
    source = isolated_project(tmp_path)
    assert (
        run_backend_query(tmp_path, "get_backend()", source_directory=source) == "sdk"
    )


def test_get_arbiter_text_model_uses_process_configuration(tmp_path: Path) -> None:
    path = write_config(tmp_path, '[backend]\narbiter_high_model="ornith-1.5-35b"\n')
    models = run_backend_query(
        tmp_path,
        "[get_arbiter_text_model('opus'), get_arbiter_text_model('haiku')]",
        path,
    )
    assert models == ["ornith-1.5-35b", "ornith-1.5-35b"]


def test_file_configuration_survives_process_restart(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        '[backend]\nbackend="arbiter"\narbiter_base_url="https://arbiter.example/v1/"\n'
        'arbiter_high_model="high-model"\narbiter_low_model="low-model"\n'
        '[agentd3]\napi_base="http://127.0.0.1:9999/"\nprose_model="configured/model"\n',
    )
    expression = (
        "[get_backend(), backend.use_arbiter_backend(), backend.get_arbiter_base_url(), "
        "get_arbiter_text_model('opus'), get_arbiter_text_model('haiku'), "
        "client._api_base(), client.get_prose_model(), backend.skip_images()]"
    )
    expected = [
        "arbiter",
        True,
        "https://arbiter.example/v1",
        "high-model",
        "low-model",
        "http://127.0.0.1:9999",
        "configured/model",
        False,
    ]
    assert run_backend_query(tmp_path, expression, path) == expected
    assert run_backend_query(tmp_path, expression, path) == expected


def test_default_config_is_project_relative_not_cwd(tmp_path: Path) -> None:
    source = isolated_project(tmp_path)
    write_config(
        source.parent,
        '[backend]\nbackend="arbiter"\n[agentd3]\nprose_model="project/model"\n',
    )
    write_config(
        tmp_path, '[backend]\nbackend="sdk"\n[agentd3]\nprose_model="wrong/model"\n'
    )
    assert run_backend_query(
        tmp_path,
        "[get_backend(), client.get_prose_model()]",
        source_directory=source,
    ) == ["arbiter", "project/model"]


def test_environment_does_not_configure_backend_or_agentd3(tmp_path: Path) -> None:
    source = isolated_project(tmp_path)
    environment = {
        name: "environment-must-not-apply" for name in BACKEND_CONFIGURATION_NAMES
    }
    assert run_backend_query(
        tmp_path,
        "[get_backend(), backend.get_arbiter_base_url(), get_arbiter_text_model('haiku'), "
        "client._api_base(), client.get_prose_model(), backend.skip_images()]",
        environment=environment,
        source_directory=source,
    ) == [
        "sdk",
        "http://10.0.0.254:8400",
        "local-coder",
        "http://127.0.0.1:8620",
        "claude/fable-5.2",
        False,
    ]


def test_runtime_overrides_are_independent_and_do_not_persist(tmp_path: Path) -> None:
    path = write_config(
        tmp_path, '[backend]\nbackend="sdk"\n[agentd3]\nprose_model="file/model"\n'
    )
    original = path.read_bytes()
    expression = (
        "[get_backend(), backend.get_arbiter_base_url(), get_arbiter_text_model('opus'), "
        "get_arbiter_text_model('haiku'), client._api_base(), client.get_prose_model()]"
    )
    assert run_backend_query(
        tmp_path,
        expression,
        path,
        setup=(
            "backend.configure(config_path=sys.argv[2], backend=' ARBITER ', "
            "arbiter_base_url='https://runtime.example/', arbiter_high_model='runtime-high', "
            "arbiter_low_model='runtime-low'); "
            "client.configure(config_path=sys.argv[2], api_base='http://127.0.0.1:9998/', prose_model='runtime/model'); "
        ),
    ) == [
        "arbiter",
        "https://runtime.example",
        "runtime-high",
        "runtime-low",
        "http://127.0.0.1:9998",
        "runtime/model",
    ]
    assert path.read_bytes() == original
    assert run_backend_query(
        tmp_path, "[get_backend(), client.get_prose_model()]", path
    ) == ["sdk", "file/model"]


def test_configure_without_arguments_clears_overrides(tmp_path: Path) -> None:
    source = isolated_project(tmp_path)
    assert run_backend_query(
        tmp_path,
        "[get_backend(), client.get_prose_model()]",
        source_directory=source,
        setup=(
            "backend.configure(backend='arbiter'); client.configure(prose_model='override/model'); "
            "backend.configure(); client.configure(); "
        ),
    ) == ["sdk", "claude/fable-5.2"]


def test_explicit_getter_config_path(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        '[backend]\nbackend="arbiter"\n[agentd3]\nprose_model="explicit/model"\n',
    )
    assert run_backend_query(
        tmp_path,
        "[get_backend(sys.argv[2]), client.get_prose_model(sys.argv[2])]",
        path,
    ) == ["arbiter", "explicit/model"]


@pytest.mark.parametrize(
    "content, message",
    [
        ("", "Configuration file is empty"),
        ("[backend", "TOMLDecodeError"),
        ('[backend]\nbackend="unknown"', "Unsupported backend"),
        ("[backend]\nbackend=1", "must be a non-empty string"),
        ('[backend]\nbackend=""', "must be a non-empty string"),
        ("[backend]\narbiter_high_model=[]", "must be a non-empty string"),
        ('[backend]\narbiter_base_url="file:///tmp/no"', "must be an HTTP(S) URL"),
        (
            '[backend]\narbiter_base_url="http://user:password@example.com"',
            "must be an HTTP(S) URL",
        ),
        ('[backend]\narbiter_base_url="http://host:bad"', "Invalid URL"),
        ('[backend]\narbiter_high_modle="typo"', "Unknown configuration field"),
        ('backend="sdk"', "must be a TOML table"),
        ('[agentd3]\napi_base=""', "must be a non-empty string"),
        ('[agentd3]\napi_base="not-a-url"', "must be an HTTP(S) URL"),
        ("[agentd3]\nprose_model=false", "must be a non-empty string"),
        ('[agentd3]\nmodel="typo"', "Unknown configuration field"),
    ],
)
def test_invalid_file_fails_closed(tmp_path: Path, content: str, message: str) -> None:
    path = write_config(tmp_path, content)
    completed = run_backend_process(tmp_path, "get_backend()", path)
    assert completed.returncode != 0
    assert message in completed.stderr
    assert not completed.stdout


def test_missing_explicit_file_fails_closed(tmp_path: Path) -> None:
    completed = run_backend_process(
        tmp_path, "get_backend()", tmp_path / "missing.toml"
    )
    assert completed.returncode != 0
    assert "FileNotFoundError" in completed.stderr


@pytest.mark.parametrize(
    "module, expression",
    [
        ("backend", "backend.get_backend()"),
        ("client", "client._request('GET', '/v1/conversations')"),
    ],
)
def test_deleted_file_after_configuration_never_falls_back(
    tmp_path: Path, module: str, expression: str
) -> None:
    path = write_config(tmp_path, '[backend]\nbackend="arbiter"\n')
    completed = run_backend_process(
        tmp_path,
        expression,
        path,
        setup=f"{module}.configure(config_path=sys.argv[2]); Path(sys.argv[2]).unlink(); ",
    )
    assert completed.returncode != 0
    assert "FileNotFoundError" in completed.stderr


@pytest.mark.parametrize("expression", ["get_backend()", "client.get_prose_model()"])
def test_corrupt_file_is_not_masked_by_runtime_override(
    tmp_path: Path, expression: str
) -> None:
    path = write_config(tmp_path, '[backend]\nbackend="sdk"\n')
    completed = run_backend_process(
        tmp_path,
        expression,
        path,
        setup=(
            "backend.configure(config_path=sys.argv[2], backend='arbiter'); "
            "client.configure(config_path=sys.argv[2], prose_model='override/model'); "
            "Path(sys.argv[2]).write_text('[backend]\\nbackend=\"invalid\"'); "
        ),
    )
    assert completed.returncode != 0
    assert "Unsupported backend" in completed.stderr


@pytest.mark.parametrize(
    "setup, message",
    [
        ("backend.configure(backend='invalid'); ", "Unsupported backend"),
        ("backend.configure(arbiter_low_model=''); ", "must be a non-empty string"),
        ("client.configure(api_base='invalid'); ", "must be an HTTP(S) URL"),
        ("client.configure(prose_model=''); ", "must be a non-empty string"),
    ],
)
def test_invalid_runtime_override_fails_closed(
    tmp_path: Path, setup: str, message: str
) -> None:
    path = write_config(tmp_path, '[backend]\nbackend="sdk"\n')
    completed = run_backend_process(tmp_path, "get_backend()", path, setup=setup)
    assert completed.returncode != 0
    assert message in completed.stderr


@pytest.mark.parametrize("expression", ["get_backend()", "client.get_prose_model()"])
def test_disappearing_default_config_fails_closed(
    tmp_path: Path, expression: str
) -> None:
    source = isolated_project(tmp_path)
    path = write_config(source.parent, '[backend]\nbackend="arbiter"\n')
    completed = run_backend_process(
        tmp_path,
        expression,
        source_directory=source,
        setup=f"get_backend(); Path({str(path)!r}).unlink(); ",
    )
    assert completed.returncode != 0
    assert "FileNotFoundError" in completed.stderr


def test_broken_default_config_symlink_fails_closed(tmp_path: Path) -> None:
    source = isolated_project(tmp_path)
    local = source.parent / "local"
    local.mkdir()
    (local / "config.toml").symlink_to(local / "missing.toml")
    completed = run_backend_process(tmp_path, "get_backend()", source_directory=source)
    assert completed.returncode != 0
    assert "FileNotFoundError" in completed.stderr
