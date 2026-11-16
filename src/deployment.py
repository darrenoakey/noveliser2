"""Deploy the local CLI; there is no daemon to restart for this project."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path


def install_cli(root: Path, target: Path) -> Path:
    root = root.resolve()
    if not (root / "run").is_file():
        raise FileNotFoundError(f"Missing CLI entrypoint: {root / 'run'}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".installing")
    temporary.write_text(f"#!/bin/sh\nexec {shlex.quote(str(root / 'run'))} \"$@\"\n", encoding="utf-8")
    temporary.chmod(0o755)
    os.replace(temporary, target)
    return target


def health(root: Path, target: Path | None = None) -> dict:
    from models import WritingStyle

    root = root.resolve()
    target = target or Path.home() / "bin" / "noveliser2"
    expected = f"exec {shlex.quote(str(root / 'run'))} \"$@\""
    if not target.is_file() or expected not in target.read_text(encoding="utf-8"):
        raise RuntimeError("Installed noveliser2 wrapper does not point at this checkout")
    if not os.access(target, os.X_OK):
        raise RuntimeError("Installed noveliser2 wrapper is not executable")
    required = {"narrative_distance", "character_voices", "rhythm", "imagery_sources",
                "positive_examples", "revision_brief"}
    if not required <= WritingStyle.model_fields.keys():
        raise RuntimeError("Deployed noveliser2 lacks the rich style schema")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=3).strip()
    return {"status": "ok", "commit": sha, "entrypoint": str(target), "source": str(root)}


def deploy(root: Path) -> dict:
    import compileall

    root = root.resolve()
    if not compileall.compile_dir(root / "src", quiet=1):
        raise RuntimeError("Source compilation failed")
    target = install_cli(root, Path.home() / "bin" / "noveliser2")
    result = subprocess.run([str(target), "health"], capture_output=True,
                            text=True, check=True, timeout=5)
    verdict = json.loads(result.stdout)
    if verdict.get("status") != "ok" or verdict.get("source") != str(root):
        raise RuntimeError("Installed CLI health verdict mismatches deployed checkout")
    receipt = root / "local" / "deployment.json"
    receipt.parent.mkdir(exist_ok=True)
    receipt.write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    return verdict
