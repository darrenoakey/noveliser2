import os
import subprocess
from pathlib import Path

GENERATE_IMAGE = Path.home() / "bin" / "generate_image"


# ##################################################################
# clean env for subprocess
# remove venv variables so external tools use their own python environment
def _clean_env() -> dict:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    paths = env.get("PATH", "").split(":")
    paths = [p for p in paths if ".venv" not in p]
    env["PATH"] = ":".join(paths)
    return env


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
# shell out to the generate_image tool with the given parameters
def _run_generate_image(prompt: str, output_path: Path, width: int, height: int) -> None:
    cmd = [
        str(GENERATE_IMAGE),
        "--prompt", prompt,
        "--width", str(width),
        "--height", str(height),
        "--output", str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=_clean_env())
    if result.returncode != 0:
        raise RuntimeError(f"Image generation failed: {result.stderr}")
