import asyncio
import hashlib
import json
from pathlib import Path

from daz_agent_sdk import ImageResult, agent
from PIL import Image, UnidentifiedImageError

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
    output_path = output_path.expanduser().absolute()
    idempotency_key = _image_idempotency_key(prompt, width, height, output_path)
    operation_state = _image_operation_state_path(output_path, idempotency_key)
    result = asyncio.run(
        agent.image(
            prompt,
            width=width,
            height=height,
            output=output_path,
            timeout=None,
            idempotency_key=idempotency_key,
            operation_state=operation_state,
        )
    )
    _validate_image_result(
        result,
        prompt=prompt,
        width=width,
        height=height,
        output_path=output_path,
        operation_state=operation_state,
        idempotency_key=idempotency_key,
    )


# ##################################################################
# image idempotency key
# binds one durable service job to the exact request and absolute artifact path
def _image_idempotency_key(
    prompt: str, width: int, height: int, output_path: Path
) -> str:
    encoded = json.dumps(
        {
            "height": height,
            "output_path": str(output_path.expanduser().absolute()),
            "prompt": prompt,
            "transparent": False,
            "width": width,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return f"noveliser2-{hashlib.sha256(encoded).hexdigest()}"


# ##################################################################
# image operation state path
# gives the SDK one stable crash-safe state file for this exact artifact
def _image_operation_state_path(output_path: Path, idempotency_key: str) -> Path:
    identity = idempotency_key.removeprefix("noveliser2-")
    return output_path.with_name(f"{output_path.name}.image-operation-{identity}.json")


# ##################################################################
# validate image result
# proves the durable Codex identity and fully decodes the exact requested artifact
def _validate_image_result(
    result: ImageResult,
    *,
    prompt: str,
    width: int,
    height: int,
    output_path: Path,
    operation_state: Path,
    idempotency_key: str,
) -> None:
    expected_path = output_path.expanduser().absolute()
    state = json.loads(operation_state.read_text())
    request = json.loads(state.get("request_body", "null"))
    expected_request = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "transparent": False,
    }
    expected_operation_id = hashlib.sha256(b"idempotency-key\0" + idempotency_key.encode()).hexdigest()
    if state.get("version") != 2 or state.get("operation_id") != expected_operation_id:
        raise RuntimeError("Mac mini Codex image service returned invalid durable operation state")
    if not result.ready or result.status != "done":
        raise RuntimeError(
            f"Mac mini Codex image job {result.job_id!r} returned non-terminal status {result.status!r}"
        )
    if result.prompt != prompt or result.width != width or result.height != height:
        raise RuntimeError(f"Mac mini Codex image job {result.job_id!r} returned mismatched request metadata")
    if result.provider != "codex" or result.model_used.provider != "codex":
        raise RuntimeError(
            f"Mac mini Codex image job {result.job_id!r} returned provider {result.provider!r}"
        )
    if not result.job_id.strip() or state.get("job_id") != result.job_id:
        raise RuntimeError("Mac mini Codex image service returned an invalid durable job identity")
    if result.idempotency_key != idempotency_key or state.get("idempotency_key") != idempotency_key:
        raise RuntimeError(f"Mac mini Codex image job {result.job_id!r} returned an invalid idempotency key")
    if request != expected_request:
        raise RuntimeError(f"Mac mini Codex image job {result.job_id!r} state does not match the exact request")
    if Path(str(state.get("output_path", ""))) != expected_path or result.path != expected_path:
        raise RuntimeError(f"Mac mini Codex image job {result.job_id!r} returned the wrong artifact path")
    _validate_image_artifact(expected_path, width, height, result.job_id)


# ##################################################################
# validate image artifact
# requires a non-empty fully decoded jpeg at exactly the requested dimensions
def _validate_image_artifact(output_path: Path, width: int, height: int, job_id: str) -> None:
    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise RuntimeError(f"Mac mini Codex image job {job_id!r} returned no non-empty artifact")
    try:
        with Image.open(output_path) as image:
            image.load()
            if image.format != "JPEG" or image.size != (width, height):
                raise RuntimeError(
                    f"Mac mini Codex image job {job_id!r} returned {image.format} {image.size}, "
                    f"expected JPEG {(width, height)}"
                )
    except (OSError, UnidentifiedImageError) as error:
        raise RuntimeError(
            f"Mac mini Codex image job {job_id!r} returned an undecodable JPEG artifact: {error}"
        ) from error


def validate_image_backend(backend: str) -> str:
    normalized = backend.strip().lower()
    if normalized == "sdk":
        return "igs"
    if normalized in LEGACY_IMAGE_BACKENDS:
        raise ValueError(DISABLED_IMAGE_BACKEND_ERROR.format(backend=backend))
    raise ValueError(f"Unsupported image backend: {backend}")
