"""Real filesystem/EPUB tests; no synthetic model or network backends."""

import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest
from pydantic import ValidationError

from book_export import (
    BookChapter,
    Manuscript,
    copy_to_icloud,
    file_sha256,
    load_manuscript,
    manuscript_from_sections,
    write_reading_editions,
)


def test_manuscript_rejects_missing_or_unordered_chapters():
    for chapters in [[], [{"number": 2, "title": "Two", "text": "Story."}],
                     [{"number": 1, "title": "One", "text": "  "}]]:
        with pytest.raises(ValidationError):
            Manuscript(title="Book", author="Writer", chapters=chapters)


def test_real_reading_editions_keep_all_prose(tmp_path: Path):
    book = Manuscript(title="Copper & Rain", author="Darren Oakey", chapters=[
        BookChapter(number=1, title="Iron & <Fire>",
                    text='Ista held the copper.\n\n“Leave it,” Mara said.\n\nThe water rose.'),
        BookChapter(number=2, title="Home", text="The bell rang once. Ista went home."),
    ])
    editions = write_reading_editions(book, tmp_path)
    assert all(path.stat().st_size > 0 for path in editions.values())
    assert load_manuscript(editions["book"]) == book
    assert "The bell rang once. Ista went home." in editions["script"].read_text()
    assert "“Leave it,” Mara said." in editions["script"].read_text()
    with zipfile.ZipFile(editions["epub"]) as archive:
        assert archive.read("mimetype") == b"application/epub+zip"
        for entry in archive.namelist():
            if entry.endswith((".xhtml", ".opf", ".ncx")):
                ElementTree.fromstring(archive.read(entry))
        chapter = archive.read("EPUB/chapter_1.xhtml").decode()
        assert "Iron &amp; &lt;Fire&gt;" in chapter
        assert "The water rose." in chapter
    restored = json.loads(editions["book"].read_text())
    assert restored["chapters"][0]["text"] == book.chapters[0].text


def test_reexport_preserves_authoritative_json_bytes(tmp_path: Path):
    path = tmp_path / "book.json"
    source = '{"title":"One","author":"Writer","provenance":"keep me","chapters":[{"number":1,"title":"Only","text":"A story."}]}\n'
    path.write_text(source)
    write_reading_editions(load_manuscript(path), tmp_path)
    assert path.read_text() == source


def test_single_chapter_epub_has_navigation(tmp_path: Path):
    book = Manuscript(title="One", author="Writer", chapters=[
        BookChapter(number=1, title="Only", text="A complete little story.")])
    editions = write_reading_editions(book, tmp_path)
    with zipfile.ZipFile(editions["epub"]) as archive:
        assert b"chapter_1.xhtml" in archive.read("EPUB/nav.xhtml")


def test_rejoin_sections_preserves_order():
    book = manuscript_from_sections("Title", "Writer", [{"number": 1, "title": "One"}],
                                    {1: {2: "After.", 1: "Before."}})
    assert book.chapters[0].text == "Before.\n\nAfter."


def test_cloud_copy_verifies_bytes_without_claiming_server_sync(tmp_path: Path):
    cloud = tmp_path / "cloud"
    cloud.mkdir()
    source = tmp_path / "book.epub"
    source.write_bytes(b"actual edition bytes")
    [destination] = copy_to_icloud([source], "A / B", cloud)
    assert destination.parent == cloud / "Books" / "A - B"
    assert file_sha256(destination) == file_sha256(source)
    assert not list(destination.parent.glob("*.uploading"))
    with pytest.raises(FileNotFoundError):
        copy_to_icloud([source], "Book", tmp_path / "not-icloud")
    source.write_bytes(b"")
    with pytest.raises(ValueError):
        copy_to_icloud([source], "Book", cloud)
