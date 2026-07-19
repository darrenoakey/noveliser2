import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from daz_agent_sdk import Capability, ImageResult, ModelInfo, Tier
from PIL import Image
import pytest

from generate_images import (
    LEGACY_IMAGE_BACKENDS,
    _image_idempotency_key,
    _image_operation_state_path,
    _validate_image_result,
    use_cover_image,
    validate_image_backend,
)


# ##################################################################
# test use cover image
# a supplied png is adopted as cover.jpg, converted to real jpeg
def test_use_cover_image_converts_to_jpeg(tmp_path: Path) -> None:
    source = tmp_path / "poster.png"
    Image.new("RGBA", (64, 96), (200, 30, 30, 255)).save(source)

    novel_dir = tmp_path / "novel"
    novel_dir.mkdir()
    cover_path = use_cover_image(source, novel_dir)

    assert cover_path == novel_dir / "cover.jpg"
    assert cover_path.exists()
    with Image.open(cover_path) as img:
        assert img.format == "JPEG"
        assert img.size == (64, 96)


def test_image_backend_routes_only_sdk_to_igs() -> None:
    assert validate_image_backend("sdk") == "igs"


@pytest.mark.parametrize("backend", sorted(LEGACY_IMAGE_BACKENDS))
def test_legacy_image_backends_fail_closed(backend: str) -> None:
    with pytest.raises(
        ValueError, match="actively disabled; use the Mac mini Codex image service"
    ):
        validate_image_backend(backend)


def test_arbiter_process_cannot_submit_image_job(tmp_path: Path) -> None:
    output_path = tmp_path / "blocked.jpg"
    source_directory = Path(__file__).resolve().parent
    process_environment = os.environ.copy()
    process_environment["NOVELISER2_BACKEND"] = "arbiter"
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.path.insert(0, sys.argv[1]); "
                "from generate_images import _run_generate_image; "
                "_run_generate_image('must remain blocked', __import__('pathlib').Path(sys.argv[2]), 32, 32)"
            ),
            str(source_directory),
            str(output_path),
        ],
        cwd=tmp_path,
        env=process_environment,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "actively disabled; use the Mac mini Codex image service" in completed.stderr
    assert not output_path.exists()


def test_image_identity_is_deterministic_for_exact_request_and_output(tmp_path: Path) -> None:
    output_path = tmp_path / "chapter.jpg"
    first = _image_idempotency_key("misty forest", 1200, 400, output_path)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; from pathlib import Path; "
                "sys.path.insert(0, sys.argv[1]); "
                "from generate_images import _image_idempotency_key; "
                "print(_image_idempotency_key(sys.argv[2], 1200, 400, Path(sys.argv[3])))"
            ),
            str(Path(__file__).resolve().parent),
            "misty forest",
            str(output_path),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.strip() == first
    assert _image_idempotency_key("changed forest", 1200, 400, output_path) != first
    assert _image_idempotency_key("misty forest", 1200, 400, tmp_path / "other.jpg") != first
    expected_state = tmp_path / f"chapter.jpg.image-operation-{first[11:]}.json"
    assert _image_operation_state_path(output_path, first) == expected_state
    changed = _image_idempotency_key("changed forest", 1200, 400, output_path)
    assert _image_operation_state_path(output_path, changed) != _image_operation_state_path(output_path, first)


def test_completed_codex_operation_validates_exact_identity_and_artifact(tmp_path: Path) -> None:
    output_path = (tmp_path / "chapter.jpg").absolute()
    Image.new("RGB", (120, 40), (20, 80, 140)).save(output_path, "JPEG")
    prompt = "misty forest"
    key = _image_idempotency_key(prompt, 120, 40, output_path)
    state_path = _image_operation_state_path(output_path, key)
    operation_id = hashlib.sha256(b"idempotency-key\0" + key.encode()).hexdigest()
    state_path.write_text(
        json.dumps(
            {
                "version": 2,
                "operation_id": operation_id,
                "idempotency_key": key,
                "request_body": json.dumps(
                    {"prompt": prompt, "width": 120, "height": 40, "transparent": False},
                    separators=(",", ":"),
                ),
                "output_intent": f"path:{output_path}",
                "output_path": str(output_path),
                "output_format": "jpeg",
                "transparent": False,
                "job_id": "durable-job-17",
            }
        )
    )
    model = ModelInfo(
        provider="codex",
        model_id="codex-image-generation",
        display_name="Codex Image Generation",
        capabilities=frozenset({Capability.IMAGE}),
        tier=Tier.HIGH,
    )
    result = ImageResult(
        path=output_path,
        model_used=model,
        conversation_id=uuid4(),
        prompt=prompt,
        width=120,
        height=40,
        job_id="durable-job-17",
        status="done",
        ready=True,
        provider="codex",
        idempotency_key=key,
    )

    _validate_image_result(
        result,
        prompt=prompt,
        width=120,
        height=40,
        output_path=output_path,
        operation_state=state_path,
        idempotency_key=key,
    )

    Image.new("RGB", (120, 40), (20, 80, 140)).save(output_path, "PNG")
    with pytest.raises(RuntimeError, match=r"returned PNG \(120, 40\), expected JPEG"):
        _validate_image_result(
            result,
            prompt=prompt,
            width=120,
            height=40,
            output_path=output_path,
            operation_state=state_path,
            idempotency_key=key,
        )

    Image.new("RGB", (121, 40), (20, 80, 140)).save(output_path, "JPEG")
    with pytest.raises(RuntimeError, match=r"returned JPEG \(121, 40\), expected JPEG \(120, 40\)"):
        _validate_image_result(
            result,
            prompt=prompt,
            width=120,
            height=40,
            output_path=output_path,
            operation_state=state_path,
            idempotency_key=key,
        )

    output_path.write_bytes(b"not an image")
    with pytest.raises(RuntimeError, match="undecodable JPEG artifact"):
        _validate_image_result(
            result,
            prompt=prompt,
            width=120,
            height=40,
            output_path=output_path,
            operation_state=state_path,
            idempotency_key=key,
        )
