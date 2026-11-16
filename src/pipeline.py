from datetime import datetime
from pathlib import Path

from colorama import Fore, Style

from audio_segments import write_chapter_audio
from backend import skip_images
from book_export import manuscript_from_sections, write_reading_editions
from break_into_chapters import break_into_chapters
from break_into_sections import break_into_sections
from create_characters import create_characters
from create_outline import create_outline
from define_writing_style import define_writing_style, enrich_writing_style
from determine_plot_type import determine_plot_type
from enhance_outline import enhance_outline
from generate_images import generate_chapter_image, generate_cover, use_cover_image
from generate_title import generate_title
from metadata import mark_book_finished, read_metadata, write_metadata
from models import (
    BookMetadata,
    BookStatus,
    Chapter,
    ChapterPlan,
    Character,
    EnhancedOutline,
    Title,
    WritingStyle,
)
from record import (
    record,
    reset_novel_dir,
    resolve_novel_dir,
    set_continue_mode,
    set_novel_dir,
)
from retrieval_memory import RetrievalMemory
from select_themes import select_themes
from write_section import write_section


# ##################################################################
# write novel
# execute the full novel generation pipeline from description to epub
def write_novel(
    description: str,
    output_dir: Path,
    num_chapters: int = 10,
    sections_per_chapter: int = 10,
    author: str = "Darren Oakey",
    continue_novel_dir: Path | None = None,
    title: str | None = None,
    style_directive: str | None = None,
    cover_image: Path | None = None,
) -> Path:
    if continue_novel_dir:
        set_continue_mode(True)
        set_novel_dir(continue_novel_dir)
        metadata = read_metadata(continue_novel_dir)
        if metadata:
            description = metadata.description
            num_chapters = metadata.num_chapters
            sections_per_chapter = metadata.sections_per_chapter
            author = metadata.author
            style_directive = metadata.style_directive or style_directive
        novel_dir = continue_novel_dir
    else:
        reset_novel_dir()
        novel_dir = None

    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Starting novel generation...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")

    # step 1: title — use the caller-supplied title verbatim, else generate one
    title_result = record(
        "Generate a title",
        lambda: Title(title=title) if title else generate_title(description),
        novel_dir or output_dir / "novel_in_progress",
    )

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
            style_directive=style_directive,
        )
        write_metadata(novel_dir, metadata)

        in_progress = output_dir / "novel_in_progress"
        if in_progress.exists():
            _move_in_progress_files(in_progress, novel_dir)

    # step 2: determine plot type
    plot_type_result = record("Determine plot type", lambda: determine_plot_type(description), novel_dir)
    plot_type_str = _extract_plot_type(plot_type_result)

    # step 3: select themes
    themes_result = record("Select themes", lambda: select_themes(description, plot_type_str), novel_dir)
    theme_values = _extract_themes(themes_result)

    # step 4: create characters
    characters_result = record(
        "Create characters", lambda: create_characters(description, plot_type_str, theme_values), novel_dir
    )
    characters = _extract_characters(characters_result)

    # step 5: create outline
    outline_text = record(
        "Create outline",
        lambda: create_outline(
            description, plot_type_str, theme_values, characters, num_chapters, sections_per_chapter
        ),
        novel_dir,
    )
    if isinstance(outline_text, dict):
        outline_text = outline_text.get("outline", str(outline_text))

    # step 6: enhance outline
    enhanced_result = record("Enhance outline", lambda: enhance_outline(outline_text), novel_dir)
    enhanced = _extract_enhanced_outline(enhanced_result)

    # step 7: define writing style
    writing_style_result = record(
        "Define writing style",
        lambda: define_writing_style(enhanced.outline, theme_values, style_directive, characters),
        novel_dir,
    )
    writing_style = _extract_writing_style(writing_style_result)
    # Old checkpoints keep their decisions and receive missing craft/voice fields
    # once. Rich styles take this path without spending another model call.
    rich_style_result = record(
        "Enrich writing style",
        lambda: enrich_writing_style(writing_style, enhanced.outline, theme_values,
                                    characters, style_directive),
        novel_dir,
    )
    writing_style = _extract_writing_style(rich_style_result)
    if not writing_style.is_rich():
        raise ValueError("Writing style enrichment did not produce a complete style sheet")

    # step 8: break into chapters
    chapter_plan_result = record(
        f"Break into {num_chapters} chapters",
        lambda: break_into_chapters(enhanced, characters, theme_values, plot_type_str, num_chapters),
        novel_dir,
    )
    chapter_plan = _extract_chapter_plan(chapter_plan_result)

    # step 9: cover image — adopt caller-supplied artwork verbatim, else generate
    cover_path = novel_dir / "cover.jpg"
    if cover_image:
        cover_path = record("Generate cover image", lambda: use_cover_image(Path(cover_image), novel_dir), novel_dir)
    elif not skip_images():
        cover_path = record(
            "Generate cover image",
            lambda: generate_cover(title_str, author, novel_dir, theme_values, plot_type_str),
            novel_dir,
        )
    if isinstance(cover_path, dict):
        cover_path = Path(cover_path.get("cover_path", novel_dir / "cover.jpg"))
    elif isinstance(cover_path, str):
        cover_path = Path(cover_path)

    # step 10: write all sections
    all_text = ""
    memory_path = novel_dir / "retrieval_memory.json"
    memory = RetrievalMemory.load(memory_path)
    content_by_chapter = {}
    lines_by_chapter: dict[int, list[dict]] = {}
    chapter_images = {}
    current_subagent_id: str | None = None

    for chapter in chapter_plan.chapters:
        content_by_chapter[chapter.number] = {}
        lines_by_chapter[chapter.number] = []

        # generate chapter image
        if not skip_images():
            chapter_img = record(
                f"Generate chapter {chapter.number} image",
                lambda ch=chapter: generate_chapter_image(ch.title, ch.chapter_goal, novel_dir, ch.number),
                novel_dir,
            )
            if isinstance(chapter_img, dict):
                chapter_images[chapter.number] = Path(
                    chapter_img.get("image_path", novel_dir / f"chapter_{chapter.number}.jpg")
                )
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
            is_final = chapter.number == num_chapters and section.number == sections_per_chapter

            def _do_write_section(
                ch=chapter, sec=section, txt=all_text, mem=memory, sub_id=current_subagent_id, final=is_final
            ):
                return write_section(
                    ch, sec, txt, mem, characters, writing_style, chapter_plan, final, subagent_id=sub_id
                )

            section_result = record(
                f"Write chapter {chapter.number} section {section.number}", _do_write_section, novel_dir
            )

            section_text, _ = _extract_section_result(section_result)
            section_lines = _extract_section_lines(section_result)
            # carry the subagent forward so the next scene continues the same
            # conversation (its context persists; orchestrator pays only for the
            # new scene prompt).
            current_subagent_id = getattr(section_result, "subagent_id", None) or (
                section_result.get("subagent_id") if isinstance(section_result, dict) else None
            )
            # embed this section into the retrieval memory (idempotent — on resume
            # a cached section is embedded here so later sections can retrieve it).
            section_id = f"ch{chapter.number}.s{section.number}"
            memory.ensure_section(section_id, section_text)
            memory.save(memory_path)
            all_text += "\n\n" + section_text
            content_by_chapter[chapter.number][section.number] = section_text
            lines_by_chapter[chapter.number].extend(section_lines)

        # speaker-labeled audio segments for this chapter, assembled from the
        # model's own tagged lines (generated, not parsed).
        record(
            f"Write chapter {chapter.number} audio",
            lambda ch=chapter, ch_lines=lines_by_chapter[chapter.number]: write_chapter_audio(
                novel_dir, ch.number, ch_lines
            ),
            novel_dir,
        )

    # step 11: create epub
    chapters_data = [ch.model_dump() if hasattr(ch, "model_dump") else ch for ch in chapter_plan.chapters]
    # Rebuild all editions from the same final prose, even on resume: cached
    # JSON paths alone do not prove an exported artifact still exists.
    editions = write_reading_editions(
        manuscript_from_sections(title_str, author, chapters_data, content_by_chapter),
        novel_dir, cover_path, chapter_images,
    )

    # An export failure must not mark a partially published book as finished.
    epub_path = str(editions["epub"])
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
# extract section result
# unwrap a SectionResult (live object or restored-from-json dict) to (text, facts)
def _extract_section_result(result):
    from models import Fact

    if hasattr(result, "text"):
        text = result.text
        raw_facts = result.new_facts
    elif isinstance(result, dict):
        text = result.get("text", "")
        raw_facts = result.get("new_facts", [])
    else:
        return str(result), []

    facts = []
    for entry in raw_facts:
        if isinstance(entry, Fact):
            facts.append(entry)
        elif isinstance(entry, dict):
            facts.append(Fact(**entry))
    return text, facts


# ##################################################################
# extract section lines
# pull the speaker-tagged lines out of a SectionResult (live or restored).
def _extract_section_lines(result) -> list[dict]:
    if hasattr(result, "lines"):
        return result.lines or []
    if isinstance(result, dict):
        return result.get("lines", [])
    return []


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
