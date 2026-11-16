import os
import subprocess
from pathlib import Path

import pytest

from deployment import health, install_cli

ROOT = Path(__file__).resolve().parent.parent


def test_install_real_cli_and_verify_its_source(tmp_path):
    target = install_cli(ROOT, tmp_path / "bin" / "noveliser2")
    result = subprocess.run([str(target), "export-book", "--help"],
                            text=True, capture_output=True, check=True, timeout=10)
    assert "--audio" in result.stdout and "--icloud" in result.stdout
    # An unrelated activated environment must not defeat venv activation.
    environment = {**os.environ, "VIRTUAL_ENV": str(tmp_path / "unrelated-venv")}
    restarted = subprocess.run([str(target), "export-book", "--help"],
                               env=environment, text=True, capture_output=True,
                               check=True, timeout=10)
    assert "--audio" in restarted.stdout
    verdict = health(ROOT, target)
    assert verdict["status"] == "ok"
    assert verdict["source"] == str(ROOT)
    assert len(verdict["commit"]) == 40
    # Reinstallation is idempotent and leaves no partial executable.
    before = target.read_bytes()
    install_cli(ROOT, target)
    assert target.read_bytes() == before
    assert not target.with_suffix(".installing").exists()


def test_health_rejects_missing_or_wrong_installation(tmp_path):
    target = tmp_path / "noveliser2"
    with pytest.raises(RuntimeError, match="does not point"):
        health(ROOT, target)
    target.write_text("#!/bin/sh\nexit 0\n")
    with pytest.raises(RuntimeError, match="does not point"):
        health(ROOT, target)
    with pytest.raises(FileNotFoundError):
        install_cli(tmp_path, target)
