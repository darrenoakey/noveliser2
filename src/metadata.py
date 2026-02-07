import json
from datetime import datetime
from pathlib import Path

from models import BookMetadata, BookStatus


# ##################################################################
# write metadata
# persist book metadata to the novel directory as json
def write_metadata(novel_dir: Path, metadata: BookMetadata) -> None:
    metadata_path = novel_dir / "metadata.json"
    metadata.updated_at = datetime.now().isoformat()
    data = metadata.model_dump()
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ##################################################################
# read metadata
# load book metadata from the novel directory
def read_metadata(novel_dir: Path) -> BookMetadata | None:
    metadata_path = novel_dir / "metadata.json"
    if not metadata_path.exists():
        return None
    with open(metadata_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return BookMetadata(**data)


# ##################################################################
# update metadata step
# mark a pipeline step as in-progress or completed in the metadata
def update_metadata_step(novel_dir: Path, step_name: str, completed: bool = False) -> None:
    metadata = read_metadata(novel_dir)
    if not metadata:
        return
    if completed:
        if step_name not in metadata.completed_steps:
            metadata.completed_steps.append(step_name)
        if metadata.current_step == step_name:
            metadata.current_step = None
    else:
        metadata.current_step = step_name
    write_metadata(novel_dir, metadata)


# ##################################################################
# mark book finished
# set the book status to finished with final artifact paths
def mark_book_finished(novel_dir: Path, epub_path: str, cover_path: str) -> None:
    metadata = read_metadata(novel_dir)
    if not metadata:
        return
    metadata.status = BookStatus.FINISHED
    metadata.epub_path = epub_path
    metadata.cover_path = cover_path
    metadata.current_step = None
    write_metadata(novel_dir, metadata)


# ##################################################################
# list books by status
# find all novels matching a given status in the output directory
def list_books_by_status(output_dir: Path, status: BookStatus) -> list[dict]:
    books = []
    if not output_dir.exists():
        return books
    for novel_dir in output_dir.iterdir():
        if not novel_dir.is_dir() or novel_dir.name in ("cache", "testing"):
            continue
        metadata = read_metadata(novel_dir)
        if metadata and metadata.status == status:
            books.append({
                "title": metadata.title,
                "description": metadata.description,
                "created_at": metadata.created_at,
                "updated_at": metadata.updated_at,
                "author": metadata.author,
                "directory": str(novel_dir),
                "current_step": metadata.current_step,
                "completed_steps": len(metadata.completed_steps),
                "epub_path": metadata.epub_path,
                "cover_path": metadata.cover_path,
            })
    books.sort(key=lambda x: x["updated_at"], reverse=True)
    return books


# ##################################################################
# find book dir by title
# locate a novel's directory by searching metadata for a matching title
def find_book_dir_by_title(output_dir: Path, title: str) -> Path | None:
    if not output_dir.exists():
        return None
    for novel_dir in output_dir.iterdir():
        if not novel_dir.is_dir() or novel_dir.name in ("cache", "testing"):
            continue
        metadata = read_metadata(novel_dir)
        if metadata and metadata.title == title:
            return novel_dir
    return None
