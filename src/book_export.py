"""Export one authoritative manuscript to reading and listening editions.

A book.json contains title, author and ordered chapters with number/title/text.
The manuscript, EPUB and narration script all derive from those same chapter texts.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from epub_generator import create_epub


class BookChapter(BaseModel):
    number: int = Field(ge=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)

    @field_validator("title", "text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Chapter title and prose must not be blank")
        return value.strip()


class Manuscript(BaseModel):
    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    description: str = ""
    chapters: list[BookChapter] = Field(min_length=1)

    @field_validator("title", "author")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Book title and author must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def ordered_chapters(self) -> Manuscript:
        if [c.number for c in self.chapters] != list(range(1, len(self.chapters) + 1)):
            raise ValueError("Chapters must be consecutive, ordered and unique, starting at 1")
        return self


def load_manuscript(path: Path) -> Manuscript:
    return Manuscript.model_validate_json(path.read_text(encoding="utf-8"))


def manuscript_from_sections(title: str, author: str, chapters: list[dict],
                             content: dict[int, dict[int, str]]) -> Manuscript:
    """Join cached sections without rewriting or reassigning any dialogue."""
    return Manuscript(title=title, author=author, chapters=[
        BookChapter(number=c["number"], title=c["title"], text="\n\n".join(
            content[c["number"]][s] for s in sorted(content[c["number"]])
        )) for c in chapters
    ])


def write_reading_editions(book: Manuscript, output_dir: Path,
                           cover: Path | None = None,
                           chapter_images: dict[int, Path] | None = None) -> dict[str, Path]:
    """Always produce an EPUB and a clean, full-text single-narrator script."""
    from audiobook import export_narration_script

    output_dir.mkdir(parents=True, exist_ok=True)
    chapters = [c.model_dump() for c in book.chapters]
    book_path = output_dir / "book.json"
    # Preserve the original authoritative bytes (including provenance fields)
    # when re-exporting. Audio and ebook can then share one source checksum.
    if not book_path.exists() or load_manuscript(book_path) != book:
        book_path.write_text(book.model_dump_json(indent=2), encoding="utf-8")
    markdown = output_dir / "manuscript.md"
    markdown.write_text(f"# {book.title}\n\nBy {book.author}\n\n" + "\n\n".join(
        f"## {c.number}. {c.title}\n\n{c.text}" for c in book.chapters
    ) + "\n", encoding="utf-8")
    result = create_epub(book.title, book.author, chapters,
                         {c.number: {1: c.text} for c in book.chapters},
                         output_dir, cover or output_dir / "cover.jpg", chapter_images)
    script = export_narration_script(chapters, book.title, output_dir)
    return {"epub": Path(result.epub_path), "script": script,
            "manuscript": markdown, "book": book_path}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_to_icloud(files: list[Path], title: str,
                   cloud_root: Path | None = None) -> list[Path]:
    """Copy and verify local iCloud Drive bytes; this does not assert server sync."""
    root = cloud_root or Path.home() / "Library/Mobile Documents/com~apple~CloudDocs"
    if not root.is_dir():
        raise FileNotFoundError(f"iCloud Drive is unavailable: {root}")
    safe_title = re.sub(r"[/\\\x00-\x1f]", "-", title).strip(". ")
    if not safe_title:
        raise ValueError("Title cannot form an iCloud folder name")
    destination = root / "Books" / safe_title
    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for source in files:
        if not source.is_file() or source.stat().st_size == 0:
            raise ValueError(f"Missing or empty edition: {source}")
        target = destination / source.name
        temporary = target.with_name(target.name + ".uploading")
        shutil.copyfile(source, temporary)
        if file_sha256(source) != file_sha256(temporary):
            temporary.unlink(missing_ok=True)
            raise OSError(f"iCloud copy checksum mismatch: {source.name}")
        temporary.replace(target)
        copied.append(target)
    return copied


def import_into_books(files: list[Path]) -> None:
    """Ask macOS Books to import actual editions; verify separately after settling."""
    for path in files:
        if path.suffix.lower() not in {".epub", ".m4b"} or not path.is_file():
            raise ValueError(f"Not a readable Books edition: {path}")
        subprocess.run(["open", "-a", "Books", str(path.resolve())], check=True,
                       capture_output=True, text=True, timeout=30)


def books_library_entries(title: str, database: Path | None = None) -> list[dict]:
    """Read Books' library, never modify it or equate an open request with import."""
    root = Path.home() / "Library/Containers/com.apple.iBooksX/Data/Documents/BKLibrary"
    candidates = [database] if database else sorted(root.glob("BKLibrary-*.sqlite"))
    if len(candidates) != 1:
        raise FileNotFoundError(f"Expected one Books library, found {len(candidates)}")
    with sqlite3.connect(candidates[0].resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute(
            "SELECT ZTITLE, ZAUTHOR, ZPATH, ZCONTENTTYPE, ZDURATION "
            "FROM ZBKLIBRARYASSET WHERE ZTITLE = ?", (title,)
        )]


def export_book(source: Path, *, audio: bool = False, icloud: bool = False,
                books: bool = False, config_path: Path | None = None) -> dict:
    book = load_manuscript(source)
    output = source.parent
    editions = write_reading_editions(book, output)
    if audio:
        from audiobook import export_audiobook
        editions["audiobook"] = export_audiobook(
            [c.model_dump() for c in book.chapters], book.title, output,
            author=book.author, config_path=config_path,
        )
    copied = copy_to_icloud(list(editions.values()), book.title) if icloud else []
    if books:
        import_into_books([p for p in editions.values() if p.suffix in {".epub", ".m4b"}])
    report = {
        "title": book.title,
        "word_count": sum(len(re.findall(r"\b[\w’'-]+\b", c.text)) for c in book.chapters),
        "editions": {kind: {"path": str(path), "sha256": file_sha256(path)}
                     for kind, path in editions.items()},
        "icloud_local_copies": [str(p) for p in copied],
        "icloud_server_sync": "not verified",
        "books_import_requested": books,
    }
    (output / "delivery.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
