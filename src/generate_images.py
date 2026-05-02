import asyncio
import base64
import io
import json
from pathlib import Path
from time import sleep
from urllib import error as urlerror
from urllib import request as urlrequest

from daz_agent_sdk import agent
from PIL import Image

from backend import get_arbiter_base_url, get_arbiter_image_model, use_arbiter_backend


# ##################################################################
# generate cover
# create an ai-generated book cover image for the novel
def generate_cover(title: str, author: str, novel_dir: Path, themes: list[str] | None = None,
                   plot_type: str | None = None) -> Path:
    theme_context = f"The story explores themes of {', '.join(themes)}. " if themes else ""
    plot_context = f"This is a {plot_type.lower()} story. " if plot_type else ""

    prompt = (
        f"Professional book cover artwork. {theme_context}{plot_context}"
        f"Atmospheric scene capturing the essence of a story titled '{title}'. "
        f"Rich colors, compelling visual design, dramatic lighting. "
        f"No text, no words, no letters, no writing of any kind. "
        f"Not a picture of a book. Pure artwork suitable for a book cover."
    )

    cover_path = novel_dir / "cover.jpg"
    _run_generate_image(prompt, cover_path, width=768, height=1024)
    return cover_path


# ##################################################################
# generate chapter image
# create a header illustration for a single chapter
def generate_chapter_image(chapter_title: str, chapter_goal: str, novel_dir: Path,
                           chapter_number: int) -> Path:
    prompt = (
        f"Artistic chapter header illustration for a chapter titled '{chapter_title}'. "
        f"The scene depicts: {chapter_goal}. "
        f"Atmospheric, moody, wide composition like a book chapter header. "
        f"No text, no words, no letters, no writing of any kind."
    )

    image_path = novel_dir / f"chapter_{chapter_number}.jpg"
    _run_generate_image(prompt, image_path, width=1200, height=400)
    return image_path


# ##################################################################
# run generate image
# calls agent.image with the given parameters
def _run_generate_image(prompt: str, output_path: Path, width: int, height: int) -> None:
    if use_arbiter_backend():
        _run_generate_image_arbiter(prompt, output_path, width, height)
        return
    asyncio.run(agent.image(prompt, width=width, height=height, output=str(output_path)))


def _arbiter_post_json(path: str, payload: dict, timeout: int = 900) -> dict:
    url = f"{get_arbiter_base_url()}{path}"
    body = json.dumps(payload).encode()
    req = urlrequest.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urlerror.HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"Arbiter request failed ({exc.code}): {detail}") from exc


def _arbiter_get_json(path: str, timeout: int = 900) -> dict:
    url = f"{get_arbiter_base_url()}{path}"
    try:
        with urlrequest.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urlerror.HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"Arbiter request failed ({exc.code}): {detail}") from exc


def _write_image_bytes(image_bytes: bytes, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() in {".jpg", ".jpeg"}:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.convert("RGB").save(output_path, format="JPEG", quality=95)
        return
    output_path.write_bytes(image_bytes)


def _run_generate_image_arbiter(prompt: str, output_path: Path, width: int, height: int) -> None:
    payload = {
        "type": "image-generate",
        "params": {
            "prompt": prompt,
            "width": width,
            "height": height,
        },
    }
    image_model = get_arbiter_image_model()
    if image_model:
        payload["model"] = image_model

    submitted = _arbiter_post_json("/v1/jobs", payload, timeout=120)
    job_id = submitted.get("job_id")
    if not job_id:
        raise ValueError(f"Arbiter did not return a job id: {submitted}")

    for _ in range(1800):
        status = _arbiter_get_json(f"/v1/jobs/{job_id}", timeout=120)
        state = status.get("status")
        if state == "completed":
            result = status.get("result") or {}
            data = result.get("data")
            if not data:
                raise ValueError(f"Arbiter image job completed without data: {status}")
            _write_image_bytes(base64.b64decode(data), output_path)
            return
        if state in {"failed", "cancelled"}:
            raise RuntimeError(f"Arbiter image job {state}: {status.get('error', status)}")
        sleep(1)
    raise TimeoutError(f"Timed out waiting for Arbiter image job {job_id}")
