import json
from datetime import datetime
from pathlib import Path

from colorama import Fore, Style

from models import (
    BookMetadata, BookStatus, Character, CharacterArc, CharacterArcs,
    Chapter, ChapterPlan, EnhancedOutline, Plot, PlotSet, Title, WritingStyle,
)
from retrieval_memory import RetrievalMemory
from record import record, reset_novel_dir, set_continue_mode, set_novel_dir, resolve_novel_dir
from metadata import write_metadata, read_metadata, mark_book_finished
from generate_title import generate_title
from determine_plot_type import determine_plot_type
from select_themes import select_themes
from create_characters import create_characters
from create_outline import create_outline
from create_plots import plan_plots, write_plot_story
from character_arcs import create_character_arcs
from enhance_outline import enhance_outline
from define_writing_style import define_writing_style
from break_into_chapters import break_into_chapters
from break_into_sections import break_into_sections
from write_section import write_section, summarize_chapter
from generate_images import generate_cover, generate_chapter_image, use_cover_image
from epub_generator import create_epub
from backend import skip_images

# The fact ledger lands in a parallel wave; integrate against it when present,
# and degrade gracefully (retrieval memory alone) when it is not yet available.
try:
    from fact_ledger import FactLedger  # type: ignore
except Exception:  # pragma: no cover - exercised only before the ledger lands
    FactLedger = None


# ##################################################################
# write novel
# execute the full novel generation pipeline from description to epub
def write_novel(description: str, output_dir: Path, num_chapters: int = 10,
                sections_per_chapter: int = 10, author: str = "Darren Oakey",
                continue_novel_dir: Path | None = None, title: str | None = None,
                style_directive: str | None = None,
                cover_image: Path | None = None) -> Path:

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

    # step 1: title — use the caller-supplied title verbatim, else generate one
    title_result = record("Generate a title",
                          lambda: Title(title=title) if title else generate_title(description),
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

    assert novel_dir is not None

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

    # step 4b: plan the plot lines (primary + subplots), then write each as a
    # standalone short story, then derive each character's arc. These feed the
    # outline/chapter/section stages so every thread braids and resolves and each
    # character lands where their arc says.
    plot_plan_result = record("Create plot plan",
                              lambda: plan_plots(description, plot_type_str, theme_values,
                                                 characters, num_chapters), novel_dir)
    plots = _extract_plot_set(plot_plan_result)

    for i, plot in enumerate(plots.plots, 1):
        story_result = record(
            f"Write plot story {i}",
            lambda p=plot, prior=plots.plots[:i - 1]: {
                "story": write_plot_story(p, prior, characters, description)
            },
            novel_dir,
        )
        plot.story = _extract_story(story_result)

    arcs_result = record("Create character arcs",
                         lambda: create_character_arcs(characters, plots), novel_dir)
    arcs = _extract_character_arcs(arcs_result)

    # step 5: create outline
    outline_text = record("Create outline",
                          lambda: create_outline(description, plot_type_str, theme_values,
                                                 characters, num_chapters, sections_per_chapter,
                                                 plots=plots, arcs=arcs), novel_dir)
    if isinstance(outline_text, dict):
        outline_text = outline_text.get("outline", str(outline_text))

    # step 6: enhance outline
    enhanced_result = record("Enhance outline",
                             lambda: enhance_outline(outline_text), novel_dir)
    enhanced = _extract_enhanced_outline(enhanced_result)

    # step 7: define writing style
    writing_style_result = record("Define writing style",
                                  lambda: define_writing_style(enhanced.outline, theme_values, style_directive), novel_dir)
    writing_style = _extract_writing_style(writing_style_result)

    # step 8: break into chapters
    chapter_plan_result = record(f"Break into {num_chapters} chapters",
                                 lambda: break_into_chapters(enhanced, characters, theme_values,
                                                             plot_type_str, num_chapters,
                                                             plots=plots, arcs=arcs), novel_dir)
    chapter_plan = _extract_chapter_plan(chapter_plan_result)

    # step 9: cover image — adopt caller-supplied artwork verbatim, else generate
    cover_path = novel_dir / "cover.jpg"
    if cover_image:
        cover_path = record("Generate cover image",
                            lambda: use_cover_image(Path(cover_image), novel_dir), novel_dir)
    elif not skip_images():
        cover_path = record("Generate cover image",
                            lambda: generate_cover(title_str, author, novel_dir, theme_values, plot_type_str), novel_dir)
    if isinstance(cover_path, dict):
        cover_path = Path(cover_path.get("cover_path", novel_dir / "cover.jpg"))
    elif isinstance(cover_path, str):
        cover_path = Path(cover_path)

    # step 10: write all sections
    all_text = ""
    memory_path = novel_dir / "retrieval_memory.json"
    memory = RetrievalMemory.load(memory_path)
    content_by_chapter = {}
    chapter_images = {}

    # fact ledger (#1/#2/#76): rebuilt deterministically every run by replaying
    # each section's stored/extracted facts through it, so resume needs no
    # separate rebuild step and old checkpoints (empty new_facts) load fine.
    ledger = FactLedger() if FactLedger is not None else None
    ledger_path = novel_dir / "fact_ledger.json"

    # compact per-chapter summaries used as long-term memory in later chapters
    # (#14). prev_section_text feeds the near-dup guard (#16) + recap (#65).
    chapter_summaries: dict[int, str] = {}
    prev_section_text = ""
    section_ordinal = 0  # integer write-order stamp for ledger facts (#3)

    for chapter in chapter_plan.chapters:
        content_by_chapter[chapter.number] = {}
        prior_summaries = _render_prior_summaries(chapter_summaries, chapter.number)

        # generate chapter image
        if not skip_images():
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

        chapter_text = ""
        for section in sections:
            is_final = (chapter.number == num_chapters and section.number == sections_per_chapter)

            section_result = record(
                f"Write chapter {chapter.number} section {section.number}",
                lambda ch=chapter, sec=section, txt=all_text, mem=memory,
                       lg=ledger, ps=prior_summaries, prev=prev_section_text: write_section(
                    ch, sec, txt, mem, characters, writing_style, chapter_plan, is_final,
                    ledger=lg, prior_summaries=ps, prev_section_text=prev,
                    novel_dir=novel_dir, plots=plots, arcs=arcs,
                ),
                novel_dir,
            )

            section_text, section_facts = _extract_section_result(section_result)
            # embed this section into the retrieval memory (idempotent — on resume
            # a cached section is embedded here so later sections can retrieve it).
            section_id = f"ch{chapter.number}.s{section.number}"
            memory.ensure_section(section_id, section_text)
            memory.save(memory_path)
            # feed facts into the ledger so canon facts accumulate as the run
            # progresses (rebuilt identically on resume from cached new_facts).
            _update_ledger(ledger, ledger_path, section_facts, section_ordinal)
            section_ordinal += 1
            all_text += "\n\n" + section_text
            chapter_text += "\n\n" + section_text
            prev_section_text = section_text
            content_by_chapter[chapter.number][section.number] = section_text

        # #14 — compact long-term summary for this completed chapter, cached as a
        # record() checkpoint so resume does not regenerate it.
        summary_result = record(
            f"Summarize chapter {chapter.number}",
            lambda ch=chapter, txt=chapter_text: {"summary": summarize_chapter(ch, txt)},
            novel_dir,
        )
        chapter_summaries[chapter.number] = _extract_summary(summary_result)

    # step 11: create epub
    chapters_data = [ch.model_dump() for ch in chapter_plan.chapters]
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
# extract plot set
# handle both pydantic model and dict formats for the plot plan. On resume
# record() returns a dict {"plots": [...]} — rebuild Plot objects (pydantic
# handles the nested dicts) so downstream mutation of plot.story works.
def _extract_plot_set(result) -> PlotSet:
    if isinstance(result, PlotSet):
        return result
    if isinstance(result, dict):
        plots = result.get("plots", [])
        return PlotSet(plots=[Plot(**p) if isinstance(p, dict) else p for p in plots])
    return PlotSet(plots=[])


# ##################################################################
# extract story
# unwrap a per-plot story record() result (live dict or restored json)
def _extract_story(result) -> str:
    if isinstance(result, dict):
        return str(result.get("story", "") or "")
    if hasattr(result, "story"):
        return str(result.story or "")
    return str(result or "")


# ##################################################################
# extract character arcs
# handle both pydantic model and dict formats for the character arcs
def _extract_character_arcs(result) -> CharacterArcs:
    if isinstance(result, CharacterArcs):
        return result
    if isinstance(result, dict):
        arcs = result.get("arcs", [])
        return CharacterArcs(arcs=[CharacterArc(**a) if isinstance(a, dict) else a for a in arcs])
    return CharacterArcs(arcs=[])


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
# render prior summaries
# join the compact summaries of all chapters before `current` into a long-term
# memory block for write_section (#14). Empty for the first chapter.
def _render_prior_summaries(summaries: dict[int, str], current: int) -> str:
    parts = []
    for num in sorted(summaries):
        if num >= current:
            continue
        text = (summaries.get(num) or "").strip()
        if text:
            parts.append(f"Chapter {num}: {text}")
    return "\n".join(parts)


# ##################################################################
# extract summary
# unwrap a chapter-summary record() result (live dict or restored json)
def _extract_summary(result) -> str:
    if isinstance(result, dict):
        return str(result.get("summary", "") or "")
    if hasattr(result, "summary"):
        return str(result.summary or "")
    return str(result or "")


# ##################################################################
# update ledger
# feed a section's facts into the fact ledger, section-stamped by integer write
# ordinal (the shape FactLedger.update expects), and persist it. Facts arrive as
# models.Fact (subject/attribute/value); the ledger speaks entity/attribute/value,
# so translate. No-op without a ledger; best-effort — a ledger hiccup never
# breaks section generation.
def _update_ledger(ledger, ledger_path: Path, facts, ordinal: int) -> None:
    if ledger is None:
        return
    try:
        payload = []
        for f in facts:
            subject = getattr(f, "subject", "") or getattr(f, "entity", "")
            attribute = getattr(f, "attribute", "")
            value = getattr(f, "value", "")
            if subject and attribute and value:
                payload.append({"entity": subject, "attribute": attribute, "value": value})
        if hasattr(ledger, "update"):
            ledger.update(payload, ordinal)
        if hasattr(ledger, "save"):
            ledger.save(ledger_path)
        elif hasattr(ledger, "to_dict"):
            ledger_path.write_text(
                json.dumps(ledger.to_dict(), indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
    except Exception:
        return


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
