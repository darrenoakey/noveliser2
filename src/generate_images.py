import asyncio
import hashlib
import json
from pathlib import Path

from daz_agent_sdk import agent, resume_image_job
from PIL import Image

from backend import get_backend


LEGACY_IMAGE_BACKENDS = {
    "arbiter",
    "spark",
    "flux",
    "mflux",
    "z",
    "z-image",
    "ollama",
    "gemini",
    "nano-banana-2",
    "openai",
}
DISABLED_IMAGE_BACKEND_ERROR = "image backend {backend!r} is actively disabled; use the Mac mini Codex image service"


# ##################################################################
# generate cover
# create an ai-generated book cover image for the novel
def generate_cover(
    title: str,
    author: str,
    novel_dir: Path,
    themes: list[str] | None = None,
    plot_type: str | None = None,
) -> Path:
    theme_context = (
        f"The story explores themes of {', '.join(themes)}. " if themes else ""
    )
    plot_context = f"This is a {plot_type.lower()} story. " if plot_type else ""

    prompt = (
        f"Professional, commercial book cover for a novel. {theme_context}{plot_context}"
        f"Atmospheric scene capturing the essence of the story. "
        f"Rich colors, compelling visual design, dramatic lighting. "
        f'Render the title text exactly as "{title}" in large, bold, highly legible '
        f"professional cover typography across the upper portion of the cover, and the "
        f'author credit exactly as "{author}" in smaller legible text near the bottom. '
        f"Spell the title and author name letter-for-letter correct, with clean kerning, "
        f"the lettering integrated tastefully into the artwork. Portrait book-cover composition."
    )

    cover_path = novel_dir / "cover.jpg"
    _run_generate_image(prompt, cover_path, width=768, height=1024)
    return cover_path


# ##################################################################
# use cover image
# adopt a caller-supplied image as the book cover instead of generating one
def use_cover_image(source: Path, novel_dir: Path) -> Path:
    cover_path = novel_dir / "cover.jpg"
    with Image.open(source) as img:
        img.convert("RGB").save(cover_path, format="JPEG", quality=95)
    return cover_path


# ##################################################################
# generate chapter image
# create a header illustration for a single chapter
def generate_chapter_image(
    chapter_title: str, chapter_goal: str, novel_dir: Path, chapter_number: int
) -> Path:
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
def _run_generate_image(
    prompt: str, output_path: Path, width: int, height: int
) -> None:
    validate_image_backend(get_backend())
    request_hash = _image_request_hash(prompt, width, height)
    job_id = _load_pending_image_job(output_path, request_hash)
    if job_id:
        result = asyncio.run(resume_image_job(job_id, output_path, timeout=900))
    else:
        result = asyncio.run(
            agent.image(
                prompt,
                width=width,
                height=height,
                output=str(output_path),
                timeout=900,
            )
        )
    if not result.ready:
        _save_pending_image_job(output_path, request_hash, result.job_id)
        raise RuntimeError(
            f"Mac mini Codex image job {result.job_id} remains durable "
            f"with status {result.status}; resume that job instead of resubmitting"
        )
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(
            f"Mac mini Codex image job {result.job_id} completed without a non-empty output"
        )
    _pending_image_job_path(output_path).unlink(missing_ok=True)


# ##################################################################
# image request hash
# identifies the exact output request so a changed prompt can start a new job
def _image_request_hash(prompt: str, width: int, height: int) -> str:
    encoded = json.dumps(
        {"prompt": prompt, "width": width, "height": height},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


# ##################################################################
# pending image job path
# keeps durable state beside the intended artifact across process restarts
def _pending_image_job_path(output_path: Path) -> Path:
    return output_path.with_name(output_path.name + ".igs-job.json")


# ##################################################################
# save pending image job
# atomically persists the durable id before returning a non-ready result
def _save_pending_image_job(output_path: Path, request_hash: str, job_id: str) -> None:
    if not job_id.strip():
        message = "Mac mini Codex image service returned no durable job id"
        raise RuntimeError(message)
    path = _pending_image_job_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps({"job_id": job_id, "request_hash": request_hash}))
    temporary.replace(path)


# ##################################################################
# load pending image job
# resumes only an exact matching durable request and never guesses an id
def _load_pending_image_job(output_path: Path, request_hash: str) -> str | None:
    path = _pending_image_job_path(output_path)
    if not path.is_file():
        return None
    record = json.loads(path.read_text())
    job_id = record.get("job_id")
    if record.get("request_hash") != request_hash or not isinstance(job_id, str):
        return None
    return job_id.strip() or None


def validate_image_backend(backend: str) -> str:
    normalized = backend.strip().lower()
    if normalized == "sdk":
        return "igs"
    if normalized in LEGACY_IMAGE_BACKENDS:
        raise ValueError(DISABLED_IMAGE_BACKEND_ERROR.format(backend=backend))
    raise ValueError(f"Unsupported image backend: {backend}")
