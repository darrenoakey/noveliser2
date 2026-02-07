from datetime import datetime
from pathlib import Path

from colorama import Fore, Style

from models import (
    BookMetadata, BookStatus, Character, Chapter, ChapterPlan,
    EnhancedOutline, WritingStyle,
)
from record import record, reset_novel_dir, set_continue_mode, set_novel_dir, resolve_novel_dir
from metadata import write_metadata, read_metadata, mark_book_finished
from generate_title import generate_title
from determine_plot_type import determine_plot_type
from select_themes import select_themes
from create_characters import create_characters
from create_outline import create_outline
from enhance_outline import enhance_outline
from define_writing_style import define_writing_style
from break_into_chapters import break_into_chapters
from break_into_sections import break_into_sections
from write_section import write_section
from generate_images import generate_cover, generate_chapter_image
from epub_generator import create_epub


# ##################################################################
# write novel
# execute the full novel generation pipeline from description to epub
def write_novel(description: str, output_dir: Path, num_chapters: int = 10,
                sections_per_chapter: int = 10, author: str = "Darren Oakey",
                continue_novel_dir: Path | None = None) -> Path:

    if continue_novel_dir:
        set_continue_mode(True)
        set_novel_dir(continue_novel_dir)
        metadata = read_metadata(continue_novel_dir)
        if metadata:
            description = metadata.description
            num_chapters = metadata.num_chapters
            sections_per_chapter = metadata.sections_per_chapter
            author = metadata.author
        novel_dir = continue_novel_dir
    else:
        reset_novel_dir()
        novel_dir = None

    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Starting novel generation...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")

    # step 1: generate title
    title_result = record("Generate a title", lambda: generate_title(description),
                          novel_dir or output_dir / "novel_in_progress")

    title_str = title_result.title if hasattr(title_result, "title") else title_result.get("title", str(title_result))

    if not continue_novel_dir:
        novel_dir = resolve_novel_dir(title_str, output_dir)
        metadata = BookMetadata(
            title=title_str,
            description=description,
            status=BookStatus.ONGOING,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            author=author,
            num_chapters=num_chapters,
            sections_per_chapter=sections_per_chapter,
        )
        write_metadata(novel_dir, metadata)

        in_progress = output_dir / "novel_in_progress"
        if in_progress.exists():
            _move_in_progress_files(in_progress, novel_dir)

    # step 2: determine plot type
    plot_type_result = record("Determine plot type",
                             lambda: determine_plot_type(description), novel_dir)
    plot_type_str = _extract_plot_type(plot_type_result)

    # step 3: select themes
    themes_result = record("Select themes",
                           lambda: select_themes(description, plot_type_str), novel_dir)
    theme_values = _extract_themes(themes_result)

    # step 4: create characters
    characters_result = record("Create characters",
                               lambda: create_characters(description, plot_type_str, theme_values), novel_dir)
    characters = _extract_characters(characters_result)

    # step 5: create outline
    outline_text = record("Create outline",
                          lambda: create_outline(description, plot_type_str, theme_values,
                                                 characters, num_chapters, sections_per_chapter), novel_dir)
    if isinstance(outline_text, dict):
        outline_text = outline_text.get("outline", str(outline_text))

    # step 6: enhance outline
    enhanced_result = record("Enhance outline",
                             lambda: enhance_outline(outline_text), novel_dir)
    enhanced = _extract_enhanced_outline(enhanced_result)

    # step 7: define writing style
    writing_style_result = record("Define writing style",
                                  lambda: define_writing_style(enhanced.outline, theme_values), novel_dir)
    writing_style = _extract_writing_style(writing_style_result)

    # step 8: break into chapters
    chapter_plan_result = record(f"Break into {num_chapters} chapters",
                                 lambda: break_into_chapters(enhanced, characters, theme_values,
                                                             plot_type_str, num_chapters), novel_dir)
    chapter_plan = _extract_chapter_plan(chapter_plan_result)

    # step 9: generate cover image
    cover_path = record("Generate cover image",
                        lambda: generate_cover(title_str, author, novel_dir, theme_values, plot_type_str), novel_dir)
    if isinstance(cover_path, dict):
        cover_path = Path(cover_path.get("cover_path", novel_dir / "cover.jpg"))
    elif isinstance(cover_path, str):
        cover_path = Path(cover_path)

    # step 10: write all sections
    all_text = ""
    facts = []
    content_by_chapter = {}
    chapter_images = {}

    for chapter in chapter_plan.chapters:
        content_by_chapter[chapter.number] = {}

        # generate chapter image
        chapter_img = record(
            f"Generate chapter {chapter.number} image",
            lambda ch=chapter: generate_chapter_image(ch.title, ch.chapter_goal, novel_dir, ch.number),
            novel_dir,
        )
        if isinstance(chapter_img, dict):
            chapter_images[chapter.number] = Path(chapter_img.get("image_path", novel_dir / f"chapter_{chapter.number}.jpg"))
        elif isinstance(chapter_img, str):
            chapter_images[chapter.number] = Path(chapter_img)
        else:
            chapter_images[chapter.number] = chapter_img

        # break chapter into sections
        section_plan_result = record(
            f"Break chapter {chapter.number} into {sections_per_chapter} sections",
            lambda ch=chapter: break_into_sections(ch, sections_per_chapter, chapter_plan.chapters),
            novel_dir,
        )
        sections = _extract_sections(section_plan_result)

        for section in sections:
            is_final = (chapter.number == num_chapters and section.number == sections_per_chapter)

            section_result = record(
                f"Write chapter {chapter.number} section {section.number}",
                lambda ch=chapter, sec=section, txt=all_text, f=facts: write_section(
                    ch, sec, txt, f, writing_style, chapter_plan, is_final
                ),
                novel_dir,
            )

            section_text = section_result.text if hasattr(section_result, "text") else section_result.get("text", "")
            new_facts = section_result.new_facts if hasattr(section_result, "new_facts") else section_result.get("new_facts", [])
            all_text += "\n\n" + section_text
            facts.extend(new_facts)
            content_by_chapter[chapter.number][section.number] = section_text

    # step 11: create epub
    chapters_data = [ch.model_dump() if hasattr(ch, "model_dump") else ch for ch in chapter_plan.chapters]
    epub_result = record(
        "Create EPUB",
        lambda: create_epub(title_str, author, chapters_data, content_by_chapter,
                            novel_dir, cover_path, chapter_images),
        novel_dir,
    )

    # mark finished
    epub_path = epub_result.epub_path if hasattr(epub_result, "epub_path") else epub_result.get("epub_path", "")
    cover_path_str = str(cover_path)
    mark_book_finished(novel_dir, epub_path, cover_path_str)

    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  Novel generation complete!{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  EPUB: {epub_path}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")

    return novel_dir


# ##################################################################
# move in progress files
# relocate temporary files to the real novel directory once title is known
def _move_in_progress_files(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    for f in src.iterdir():
        if f.is_file():
            target = dst / f.name
            if not target.exists():
                f.rename(target)
    if not any(src.iterdir()):
        src.rmdir()


# ##################################################################
# extract plot type
# handle both pydantic model and dict formats for plot type
def _extract_plot_type(result) -> str:
    if hasattr(result, "plot_type"):
        pt = result.plot_type
        return pt.value if hasattr(pt, "value") else str(pt)
    if isinstance(result, dict):
        return result.get("plot_type", str(result))
    return str(result)


# ##################################################################
# extract themes
# handle both pydantic model and dict formats for themes
def _extract_themes(result) -> list[str]:
    if hasattr(result, "themes"):
        return [t.value if hasattr(t, "value") else str(t) for t in result.themes]
    if isinstance(result, dict):
        return result.get("themes", [])
    return []


# ##################################################################
# extract characters
# handle both pydantic model and dict formats for characters
def _extract_characters(result) -> list[Character]:
    if hasattr(result, "characters"):
        chars = result.characters
        if chars and isinstance(chars[0], Character):
            return chars
        return [Character(**c) if isinstance(c, dict) else c for c in chars]
    if isinstance(result, dict):
        return [Character(**c) for c in result.get("characters", [])]
    return []


# ##################################################################
# extract enhanced outline
# handle both pydantic model and dict formats for enhanced outline
def _extract_enhanced_outline(result) -> EnhancedOutline:
    if isinstance(result, EnhancedOutline):
        return result
    if isinstance(result, dict):
        return EnhancedOutline(**result)
    return EnhancedOutline(outline=str(result), humor_elements=[], romance_elements=[])


# ##################################################################
# extract writing style
# handle both pydantic model and dict formats for writing style
def _extract_writing_style(result) -> WritingStyle:
    if isinstance(result, WritingStyle):
        return result
    if isinstance(result, dict):
        return WritingStyle(**result)
    return WritingStyle(style_description=str(result), tone="", voice="", pacing="", examples=[])


# ##################################################################
# extract chapter plan
# handle both pydantic model and dict formats for chapter plan
def _extract_chapter_plan(result) -> ChapterPlan:
    if isinstance(result, ChapterPlan):
        return result
    if isinstance(result, dict):
        chapters = result.get("chapters", [])
        return ChapterPlan(chapters=[Chapter(**c) if isinstance(c, dict) else c for c in chapters])
    return ChapterPlan(chapters=[])


# ##################################################################
# extract sections
# handle both pydantic model and dict formats for sections
def _extract_sections(result) -> list:
    if hasattr(result, "sections"):
        return result.sections
    if isinstance(result, dict):
        from models import Section
        return [Section(**s) for s in result.get("sections", [])]
    return []
