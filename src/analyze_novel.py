"""Prose-quality metrics for a generated novel.

Standalone, dependency-light analyzer that reads the cached section JSONs in an
``output/<Title>/`` directory and reports the exact classes of defect found by
manual inspection of real runs:

* **Repeated multi-word phrases** — the top-N most over-used n-grams across all
  sections (e.g. "the weight of" x217, "ghost" x245 in a real prior novel).
* **Near-duplicate sections** — pairs of sections whose text is textually very
  similar (``difflib.SequenceMatcher`` ratio above a threshold), catching bugs
  like the two ~94%-identical chapter-10 sections found by hand.
* **Basic per-section stats** — word count, sentence count, adjective density
  as a cheap cliche-adjacent signal.

Runs without the generation pipeline or any model backend:

    .venv/bin/python -m src.analyze_novel "<Title>"
    .venv/bin/python -m src.analyze_novel /path/to/output/<Title> --top 30

Writes ``quality_report.json`` into the analysed directory and prints a summary.
It never modifies section checkpoints or any other pipeline file.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

# ##################################################################
# constants
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / "output"
REPORT_NAME = "quality_report.json"

# section checkpoint files look like chapter_1_section_2.json
SECTION_RE = re.compile(r"^chapter_(\d+)_section_(\d+)\.json$")
# keep both the ASCII apostrophe and the typographic right single quote (U+2019),
# which real generated prose uses, so contractions/possessives stay one token
_WORD_RE = re.compile(r"[A-Za-z'’]+")
_SENT_RE = re.compile(r"[.!?]+")

# small closed-class stop set so common function-word runs ("out of the",
# "one of the") don't dominate the repeated-phrase report
_STOPWORDS = frozenset(
    "the a an and or but of to in on at for with from by as is was were be been "
    "being it its it's he she they them his her their you your i we our that this "
    "these those had has have do did not no so if then than there here".split()
)

# a deliberately small, high-precision set of common English adjectives used as
# a cheap adjective-density proxy (no POS tagger dependency)
_COMMON_ADJECTIVES = frozenset(
    "small big large little old new young good bad great high low long short "
    "old cold hot warm dark light bright pale soft hard heavy quiet loud slow "
    "fast deep thin wide narrow empty full dead alive silent still sharp "
    "beautiful terrible quiet strange sudden gentle rough smooth broken distant "
    "faint dim vast enormous tiny huge grey gray white black red blue green "
    "golden silver silent weary tired grim bleak hollow ancient".split()
)


# ##################################################################
# section
# one loaded section: its chapter/section indices and its prose text
@dataclass
class LoadedSection:
    chapter: int
    number: int
    path: Path
    text: str

    # human-readable label like "ch3.s2"
    @property
    def label(self) -> str:
        return f"ch{self.chapter}.s{self.number}"


# ##################################################################
# section stats
# per-section basic metrics
@dataclass
class SectionStats:
    label: str
    word_count: int
    sentence_count: int
    adjective_count: int
    adjective_density: float


# ##################################################################
# phrase hit
# a repeated multi-word phrase and how often it occurs
@dataclass
class PhraseHit:
    phrase: str
    n: int
    count: int


# ##################################################################
# duplicate pair
# a pair of sections flagged as textually near-identical
@dataclass
class DuplicatePair:
    a: str
    b: str
    ratio: float
    consecutive_same_chapter: bool


# ##################################################################
# quality report
# the full analysis result for one novel directory
@dataclass
class QualityReport:
    title: str
    directory: str
    section_count: int
    total_words: int
    repeated_phrases: list[PhraseHit] = field(default_factory=list)
    duplicate_pairs: list[DuplicatePair] = field(default_factory=list)
    section_stats: list[SectionStats] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "directory": self.directory,
            "section_count": self.section_count,
            "total_words": self.total_words,
            "repeated_phrases": [asdict(p) for p in self.repeated_phrases],
            "duplicate_pairs": [asdict(d) for d in self.duplicate_pairs],
            "section_stats": [asdict(s) for s in self.section_stats],
        }


# ##################################################################
# resolve directory
# accept either a bare title (resolved under output/) or a full path
def resolve_directory(title_or_path: str) -> Path:
    p = Path(title_or_path)
    if p.is_dir():
        return p.resolve()
    candidate = OUTPUT_DIR / title_or_path
    if candidate.is_dir():
        return candidate.resolve()
    raise FileNotFoundError(
        f"No such novel directory: '{title_or_path}' "
        f"(looked at '{p}' and '{candidate}')"
    )


# ##################################################################
# load sections
# read every chapter_N_section_M.json in a directory, sorted by (chapter, section)
def load_sections(directory: Path) -> list[LoadedSection]:
    sections: list[LoadedSection] = []
    for path in directory.iterdir():
        m = SECTION_RE.match(path.name)
        if not m:
            continue
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        text = data.get("text", "") if isinstance(data, dict) else ""
        if not isinstance(text, str):
            text = ""
        sections.append(
            LoadedSection(
                chapter=int(m.group(1)),
                number=int(m.group(2)),
                path=path,
                text=text,
            )
        )
    sections.sort(key=lambda s: (s.chapter, s.number))
    return sections


# ##################################################################
# tokenize
# lowercase word tokens, apostrophes kept (so "it's" stays one token)
def tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


# ##################################################################
# count phrases
# count repeated n-grams (for n in ns) across all provided texts. an n-gram is
# ignored if every one of its words is a stopword, so pure function-word runs
# don't swamp the report. returns the top-N by count (count >= min_count only).
def count_phrases(
    texts: list[str],
    ns: tuple[int, ...] = (2, 3, 4),
    top: int = 25,
    min_count: int = 3,
) -> list[PhraseHit]:
    counters: dict[int, Counter] = {n: Counter() for n in ns}
    for text in texts:
        tokens = tokenize(text)
        for n in ns:
            if len(tokens) < n:
                continue
            for i in range(len(tokens) - n + 1):
                gram = tokens[i : i + n]
                if all(w in _STOPWORDS for w in gram):
                    continue
                counters[n][" ".join(gram)] += 1

    hits: list[PhraseHit] = []
    for n in ns:
        for phrase, count in counters[n].items():
            if count >= min_count:
                hits.append(PhraseHit(phrase=phrase, n=n, count=count))
    # most repeated first; longer phrases win ties (more specific/notable)
    hits.sort(key=lambda h: (h.count, h.n), reverse=True)
    return hits[:top]


# ##################################################################
# similarity
# textual similarity ratio between two prose strings in [0, 1], compared at the
# WORD level. Word tokens (~1k per section) are far cheaper than raw chars (~6k)
# for SequenceMatcher's O(n^2) match, and word-level overlap is a more faithful
# signal of near-duplicate prose than character overlap (any two English
# passages share a nearly identical character multiset).
def similarity(a: str, b: str) -> float:
    ta, tb = tokenize(a), tokenize(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return SequenceMatcher(None, ta, tb, autojunk=False).ratio()


# ##################################################################
# find duplicates
# flag section pairs whose similarity >= threshold. when consecutive_only is
# True, only compares neighbouring sections within the same chapter (cheap);
# otherwise compares every pair.
def find_duplicates(
    sections: list[LoadedSection],
    threshold: float = 0.6,
    consecutive_only: bool = False,
) -> list[DuplicatePair]:
    pairs: list[DuplicatePair] = []
    tokens = [tokenize(s.text) for s in sections]
    n = len(sections)
    for i in range(n):
        js = [i + 1] if consecutive_only else range(i + 1, n)
        for j in js:
            if j >= n:
                continue
            a, b = sections[i], sections[j]
            consec = a.chapter == b.chapter and abs(a.number - b.number) == 1
            if consecutive_only and not consec:
                continue
            ta, tb = tokens[i], tokens[j]
            # cheap length-ratio upper bound: SequenceMatcher.ratio() can never
            # exceed 2*min(len)/(len_a+len_b), so skip pairs too different in
            # size to clear the threshold before the O(n^2) match
            if not ta or not tb:
                continue
            la, lb = len(ta), len(tb)
            if 2 * min(la, lb) / (la + lb) < threshold:
                continue
            ratio = SequenceMatcher(None, ta, tb, autojunk=False).ratio()
            if ratio >= threshold:
                pairs.append(
                    DuplicatePair(
                        a=a.label,
                        b=b.label,
                        ratio=round(ratio, 4),
                        consecutive_same_chapter=consec,
                    )
                )
    pairs.sort(key=lambda p: p.ratio, reverse=True)
    return pairs


# ##################################################################
# section stats
# per-section word/sentence counts and adjective density
def section_stats(section: LoadedSection) -> SectionStats:
    words = tokenize(section.text)
    word_count = len(words)
    sentence_count = len([s for s in _SENT_RE.split(section.text) if s.strip()])
    adj = sum(1 for w in words if w in _COMMON_ADJECTIVES)
    density = round(adj / word_count, 4) if word_count else 0.0
    return SectionStats(
        label=section.label,
        word_count=word_count,
        sentence_count=sentence_count,
        adjective_count=adj,
        adjective_density=density,
    )


# ##################################################################
# analyze
# run the full analysis over a loaded directory and build the report
def analyze(
    directory: Path,
    top: int = 25,
    dup_threshold: float = 0.6,
    consecutive_only: bool = False,
) -> QualityReport:
    sections = load_sections(directory)
    texts = [s.text for s in sections]
    stats = [section_stats(s) for s in sections]
    return QualityReport(
        title=directory.name,
        directory=str(directory),
        section_count=len(sections),
        total_words=sum(s.word_count for s in stats),
        repeated_phrases=count_phrases(texts, top=top),
        duplicate_pairs=find_duplicates(
            sections, threshold=dup_threshold, consecutive_only=consecutive_only
        ),
        section_stats=stats,
    )


# ##################################################################
# format report
# human-readable summary of a report for stdout
def format_report(report: QualityReport, top: int = 25) -> str:
    lines: list[str] = []
    lines.append(f"Quality report for: {report.title}")
    lines.append(f"  directory:  {report.directory}")
    lines.append(f"  sections:   {report.section_count}")
    lines.append(f"  total words:{report.total_words}")
    lines.append("")

    lines.append(f"Top repeated phrases (>= 3 occurrences, top {top}):")
    if report.repeated_phrases:
        for h in report.repeated_phrases:
            lines.append(f"  {h.count:5d}  ({h.n}-gram)  {h.phrase!r}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("Near-duplicate section pairs:")
    if report.duplicate_pairs:
        for d in report.duplicate_pairs:
            flag = "  [consecutive same-chapter]" if d.consecutive_same_chapter else ""
            lines.append(f"  {d.ratio:.3f}  {d.a} <-> {d.b}{flag}")
    else:
        lines.append("  (none above threshold)")
    lines.append("")

    if report.section_stats:
        counts = [s.word_count for s in report.section_stats]
        dens = [s.adjective_density for s in report.section_stats]
        lines.append("Per-section stats:")
        lines.append(
            f"  word count  min/avg/max: "
            f"{min(counts)}/{sum(counts) // len(counts)}/{max(counts)}"
        )
        lines.append(
            f"  adj density min/avg/max: "
            f"{min(dens):.3f}/{sum(dens) / len(dens):.3f}/{max(dens):.3f}"
        )
    return "\n".join(lines)


# ##################################################################
# write report
# persist the JSON report into the novel directory
def write_report(report: QualityReport, directory: Path) -> Path:
    out_path = directory / REPORT_NAME
    out_path.write_text(json.dumps(report.to_dict(), indent=2))
    return out_path


# ##################################################################
# main
# CLI entry point
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure prose-quality/consistency problems in a generated novel."
    )
    parser.add_argument(
        "title",
        help="Novel title (resolved under output/) or a path to an output/<Title> dir",
    )
    parser.add_argument(
        "--top", type=int, default=25, help="Number of top repeated phrases to report"
    )
    parser.add_argument(
        "--dup-threshold",
        type=float,
        default=0.6,
        help="Similarity ratio at/above which section pairs are flagged as duplicates",
    )
    parser.add_argument(
        "--consecutive-only",
        action="store_true",
        help="Only compare consecutive sections within the same chapter (faster)",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print the report but do not write quality_report.json",
    )
    args = parser.parse_args(argv)

    directory = resolve_directory(args.title)
    report = analyze(
        directory,
        top=args.top,
        dup_threshold=args.dup_threshold,
        consecutive_only=args.consecutive_only,
    )
    print(format_report(report, top=args.top))
    if not args.no_write:
        out_path = write_report(report, directory)
        print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
