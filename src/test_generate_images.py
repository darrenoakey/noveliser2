from pathlib import Path

from PIL import Image

from generate_images import use_cover_image


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
