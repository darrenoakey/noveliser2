"""Non-secret configuration from local/config.toml, with explicit CLI overrides.

The default file is optional and anchored to the project, never the caller's cwd.
An explicitly selected file must exist. Existing invalid files always raise,
including when process overrides would otherwise mask the invalid values.
"""

import tomllib
from pathlib import Path
from urllib.parse import urlsplit

SDK_BACKEND = "sdk"
ARBITER_BACKEND = "arbiter"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "local" / "config.toml"

_FIELDS = {
    "backend": {
        "backend",
        "arbiter_base_url",
        "arbiter_high_model",
        "arbiter_low_model",
    },
    "agentd3": {"api_base", "prose_model"},
}
_config_path: Path | None = None
_overrides: dict[str, str] = {}
_default_config_seen = False


def _validate_section(section: str, values: dict) -> dict[str, str]:
    if not isinstance(values, dict):
        raise TypeError(f"[{section}] must be a TOML table")
    for key, value in values.items():
        if key not in _FIELDS[section]:
            raise ValueError(f"Unknown configuration field: {section}.{key}")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{section}.{key} must be a non-empty string")
        if key == "backend" and value.strip().lower() not in {
            SDK_BACKEND,
            ARBITER_BACKEND,
        }:
            raise ValueError(f"Unsupported backend: {value}")
        if key in {"api_base", "arbiter_base_url"}:
            try:
                parsed = urlsplit(value.strip())
                valid = (
                    parsed.scheme in {"http", "https"}
                    and bool(parsed.hostname)
                    and parsed.port != 0
                    and parsed.username is None
                    and parsed.password is None
                    and not parsed.query
                    and not parsed.fragment
                    and not any(char.isspace() for char in value.strip())
                )
            except ValueError as exc:
                raise ValueError(f"Invalid URL for {section}.{key}") from exc
            if not valid:
                raise ValueError(
                    f"{section}.{key} must be an HTTP(S) URL without credentials, query or fragment"
                )
    return {key: value.strip() for key, value in values.items()}


def read_configuration(
    config_path: str | Path | None = None,
) -> dict[str, dict[str, str]]:
    """Read and validate both known tables; unrelated tables are left to their owners."""
    global _default_config_seen
    path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
    try:
        with path.open("rb") as stream:
            if config_path is None:
                _default_config_seen = True
            document = tomllib.load(stream)
    except FileNotFoundError:
        if config_path is not None or _default_config_seen or path.is_symlink():
            raise
        return {}
    if not document:
        raise ValueError(f"Configuration file is empty: {path}")
    return {
        section: _validate_section(section, document[section])
        for section in _FIELDS
        if section in document
    }


def configure(
    *,
    backend: str | None = None,
    arbiter_base_url: str | None = None,
    arbiter_high_model: str | None = None,
    arbiter_low_model: str | None = None,
    config_path: str | Path | None = None,
) -> None:
    """Replace backend-only process overrides; configure() resets to the default file.

    None means no override. The file is still validated before overrides apply.
    This never writes configuration; persist settings in local/config.toml.
    """
    global _config_path, _overrides
    values = {
        "backend": backend,
        "arbiter_base_url": arbiter_base_url,
        "arbiter_high_model": arbiter_high_model,
        "arbiter_low_model": arbiter_low_model,
    }
    overrides = _validate_section(
        "backend", {key: value for key, value in values.items() if value is not None}
    )
    selected_path = Path(config_path).resolve() if config_path is not None else None
    read_configuration(selected_path)
    _config_path, _overrides = selected_path, overrides


def _settings(config_path: str | Path | None = None) -> dict[str, str]:
    document = read_configuration(
        config_path if config_path is not None else _config_path
    )
    return document.get("backend", {}) | _overrides


def get_backend(config_path: str | Path | None = None) -> str:
    return _settings(config_path).get("backend", SDK_BACKEND).lower()


def use_arbiter_backend(config_path: str | Path | None = None) -> bool:
    return get_backend(config_path) == ARBITER_BACKEND


def get_arbiter_base_url(config_path: str | Path | None = None) -> str:
    return (
        _settings(config_path)
        .get("arbiter_base_url", "http://10.0.0.254:8400")
        .rstrip("/")
    )


def get_arbiter_text_model(model: str, config_path: str | Path | None = None) -> str:
    settings = _settings(config_path)
    high_model = settings.get("arbiter_high_model", "local-coder")
    return (
        settings.get("arbiter_low_model", high_model)
        if model == "haiku"
        else high_model
    )


def skip_images() -> bool:
    # Covers and chapter images are ALWAYS generated, independent of text routing.
    return False
