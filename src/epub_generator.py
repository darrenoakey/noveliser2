import uuid
from pathlib import Path

from ebooklib import epub

from models import EpubResult


# ##################################################################
# create epub
# assemble all content into a properly formatted epub file
def create_epub(title: str, author: str, chapters_data: list[dict],
                content_by_chapter: dict[int, dict[int, str]],
                novel_dir: Path, cover_path: Path,
                chapter_images: dict[int, Path] | None = None) -> EpubResult:
    book = epub.EpubBook()

    book.set_identifier(str(uuid.uuid4()))
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    if cover_path.exists():
        with open(cover_path, "rb") as f:
            book.set_cover("cover.jpg", f.read(), create_page=True)

    css_content = """
body { font-family: Georgia, serif; line-height: 1.6; margin: 2em; }
h1 { text-align: center; margin-top: 2em; margin-bottom: 1em; font-size: 1.8em; }
p { text-indent: 1.5em; margin: 0.3em 0; }
p:first-of-type { text-indent: 0; }
.chapter-image { text-align: center; margin: 1em 0; }
.chapter-image img { max-width: 100%; height: auto; }
"""
    style = epub.EpubItem(uid="style", file_name="style/default.css", media_type="text/css", content=css_content.encode())
    book.add_item(style)

    epub_chapters = []
    spine = ["nav"]
    num_chapters = len(content_by_chapter)

    for chapter_num in sorted(content_by_chapter.keys()):
        chapter_data = chapters_data[chapter_num - 1]
        section_content = content_by_chapter[chapter_num]

        if num_chapters > 1:
            chapter_title_text = chapter_data.get("title", f"Chapter {chapter_num}")
            html_content = f'<h1>Chapter {chapter_num}: {chapter_title_text}</h1>\n'
            toc_title = f"Chapter {chapter_num}: {chapter_title_text}"
        else:
            html_content = f"<h1>{title}</h1>\n"
            toc_title = title

        if chapter_images and chapter_num in chapter_images:
            img_path = chapter_images[chapter_num]
            if img_path.exists():
                img_name = f"images/chapter_{chapter_num}.jpg"
                with open(img_path, "rb") as f:
                    img_item = epub.EpubItem(
                        uid=f"chapter_img_{chapter_num}",
                        file_name=img_name,
                        media_type="image/jpeg",
                        content=f.read(),
                    )
                book.add_item(img_item)
                html_content += f'<div class="chapter-image"><img src="{img_name}" alt="Chapter {chapter_num}"/></div>\n'

        for section_num in sorted(section_content.keys()):
            section_text = section_content[section_num]
            if isinstance(section_text, str):
                paragraphs = section_text.split("\n\n")
                for para in paragraphs:
                    stripped = para.strip()
                    if stripped:
                        escaped = stripped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        html_content += f"<p>{escaped}</p>\n"

        epub_chapter = epub.EpubHtml(
            title=toc_title,
            file_name=f"chapter_{chapter_num}.xhtml",
            lang="en",
        )
        epub_chapter.content = html_content
        epub_chapter.add_item(style)

        book.add_item(epub_chapter)
        epub_chapters.append(epub_chapter)
        spine.append(epub_chapter)

    if num_chapters > 1:
        book.toc = epub_chapters

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    safe_title = title.replace(":", " -").replace("/", "-")
    epub_path = novel_dir / f"{safe_title}.epub"
    epub.write_epub(str(epub_path), book, {})

    return EpubResult(epub_path=str(epub_path), cover_path=str(cover_path))
