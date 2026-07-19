import json
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image
import pytest

from generate_images import (
    LEGACY_IMAGE_BACKENDS,
    _image_request_hash,
    _load_pending_image_job,
    _pending_image_job_path,
    _save_pending_image_job,
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


def test_pending_durable_image_job_survives_restart_and_matches_exact_request(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "chapter.jpg"
    request_hash = _image_request_hash("misty forest", 1200, 400)
    _save_pending_image_job(output_path, request_hash, "durable-job-17")

    assert _load_pending_image_job(output_path, request_hash) == "durable-job-17"
    assert (
        _load_pending_image_job(
            output_path, _image_request_hash("changed forest", 1200, 400)
        )
        is None
    )
    record = _pending_image_job_path(output_path)
    assert json.loads(record.read_text())["job_id"] == "durable-job-17"
    assert not record.with_suffix(record.suffix + ".new").exists()
