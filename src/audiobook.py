"""Resumable remote Kokoro narration and chaptered M4B export.

No local models or implicit fallback. Call export_audiobook repeatedly after
AudiobookPending (e.g. from a background worker). Completed chunks and remote job
IDs survive process restarts. Only stdlib + ffmpeg/ffprobe are required; an
optional authenticated endpoint additionally requires the daz-secrets SDK.

local/config.toml::

    [audiobook]
    base_url = "http://10.0.0.254:8400"
    voice = "bf_emma"
    speed = 0.98
    # token_service = "arbiter"  # optional daz-secrets reference, NOT a token
    # token_account = "api-key"
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import re
import subprocess
import tomllib
import wave
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class NarrationChapter:
    title: str
    text: str


class AudiobookPending(RuntimeError):
    """Remote work is persisted; retry the SAME export later, without resubmitting."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Audiobook synthesis pending: {job_id}")


def _synthesis_capacity(pending: list[str]) -> int:
    """Bound the shared GPU queue to three simultaneous jobs per export."""
    return max(0, 3 - len(pending))


def clean_narration(text: str) -> str:
    """Strip explicit production directions/Markdown, never paraphrase story prose.

    Only standalone bracketed directions are removed: inline brackets may be
    part of the story. Ambiguous inline production directions fail closed.
    """
    if not isinstance(text, str):
        raise TypeError("Narration must be text")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.fullmatch(r"\*{3,}|-{3,}|_{3,}", stripped):
            continue
        if re.fullmatch(
            r"\[(?:pause|sfx|music|sound effect|stage direction|narrator direction|"
            r"whisper|laugh|sigh|silence|beat|breath|speaking|read|in a whisper)\b[^\[\]]*\]",
            stripped, re.IGNORECASE,
        ):
            continue
        if re.match(r"^(?:stage direction|sfx|music|sound effect|narrator direction)\s*:", stripped, re.IGNORECASE):
            continue
        if re.search(r"\[(?:pause|sfx|music|sound effect|whisper|laugh|sigh|stage direction)\b[^]]*\]", stripped, re.IGNORECASE):
            raise ValueError("Inline production direction: move it to a separate line before export")
        line = re.sub(r"^\s*#{1,6}\s+", "", line)
        line = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__", lambda m: m[1] or m[2], line)
        line = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"\1", line)
        lines.append(line.rstrip())
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    if not result or not re.search(r"\w", result):
        raise ValueError("Empty narration")
    return result


def _chapters(chapters: list[NarrationChapter | dict]) -> list[NarrationChapter]:
    if not chapters:
        raise ValueError("At least one chapter is required")
    result = []
    for index, item in enumerate(chapters, 1):
        title = item.title if isinstance(item, NarrationChapter) else item.get("title", f"Chapter {index}")
        text = item.text if isinstance(item, NarrationChapter) else item["text"]
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Every chapter needs a title")
        result.append(NarrationChapter(" ".join(title.split()), clean_narration(text)))
    return result


def split_narration(text: str, max_chars: int = 420) -> list[str]:
    """Bound every TTS input and prove full ordered character coverage.

    Kokoro's context is finite; sentence-sized inputs avoid server-side context
    truncation. Whitespace normalization is the ONLY change made here.
    """
    if max_chars < 40 or max_chars > 420:
        raise ValueError("max_chars must be between 40 and 420")
    normalized = " ".join(text.split())
    if not normalized:
        raise ValueError("Empty narration")
    words = normalized.split(" ")
    chunks, current = [], ""
    for word in words:
        if len(word) > max_chars:
            raise ValueError("Unpronounceable overlong token; edit source rather than truncate")
        if current and len(current) + len(word) + 1 > max_chars:
            chunks.append(current)
            current = ""
        current = f"{current} {word}".strip()
        # Prefer complete sentences, but don't produce dozens of tiny fragments.
        if len(current) >= max_chars // 2 and re.search(r'[.!?][\"”’\']?$', word):
            chunks.append(current)
            current = ""
    if current:
        chunks.append(current)
    if " ".join(chunks) != normalized:
        raise RuntimeError("Narration chunk coverage mismatch")
    return chunks


def _safe_title(title: str) -> str:
    name = re.sub(r"[\x00-\x1f/\\:]", "-", title).strip(" .")
    if not name:
        raise ValueError("Empty book title")
    return name[:160]


def _atomic(path: Path, data: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_bytes(data)
    temporary.replace(path)


def _json(path: Path, value: dict) -> None:
    _atomic(path, json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"))


def export_narration_script(chapters: list, title: str, output_dir: Path) -> Path:
    """Write UTF-8 spoken copy, with chapter titles but no acting directions."""
    normalized = _chapters(chapters)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{_safe_title(title)}.narration.txt"
    _atomic(path, (title.strip() + "\n\n" + "\n\n".join(
        f"{chapter.title}\n\n{chapter.text}" for chapter in normalized
    ) + "\n").encode("utf-8"))
    return path


def _settings(path: Path | None) -> dict:
    path = path or Path(__file__).resolve().parent.parent / "local" / "config.toml"
    config = tomllib.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}
    settings = {"base_url": "http://10.0.0.254:8400", "voice": "bf_emma", "speed": 0.98}
    settings.update(config.get("audiobook", {}))
    allowed = {"base_url", "voice", "speed", "token_service", "token_account"}
    if set(settings) - allowed:
        raise ValueError("Unknown audiobook configuration field (credentials must use daz-secrets)")
    parsed = urlsplit(settings["base_url"])
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query:
        raise ValueError("Invalid audiobook base_url; credentials in URLs are forbidden")
    if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Audiobook synthesis must use a remote service")
    if not 0.5 <= float(settings["speed"]) <= 2.0:
        raise ValueError("Audiobook speed must be 0.5–2.0")
    if bool(settings.get("token_service")) != bool(settings.get("token_account")):
        raise ValueError("Both daz-secrets reference fields are required")
    return settings


def _remote(settings: dict, suffix: str, payload: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if settings.get("token_service"):
        import daz_secrets

        secret = daz_secrets.Client().get(settings["token_service"], settings["token_account"])
        token = secret.decode("utf-8") if isinstance(secret, bytes) else secret
        headers["Authorization"] = f"Bearer {token}"
    req = Request(settings["base_url"].rstrip("/") + suffix,
                  data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
    try:
        with urlopen(req, timeout=30) as response:
            return json.load(response)
    except (OSError, ValueError):
        # Never propagate HTTP error bodies or headers containing credentials.
        raise RuntimeError("Remote audiobook service request failed; persisted work retained") from None


def _wav_info(path: Path) -> tuple[int, int, int, int]:
    with wave.open(str(path), "rb") as audio:
        if audio.getcomptype() != "NONE" or audio.getnframes() <= 0:
            raise ValueError("Invalid or empty synthesis WAV")
        info = audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes()
        if len(audio.readframes(info[3])) != info[0] * info[1] * info[3]:
            raise ValueError("Truncated synthesis WAV")
        return info


def _run(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, timeout=240, check=False)
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} failed: {result.stderr[-1500:]}")
    return result.stdout


def _escape_meta(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\n", " ").replace("=", "\\=").replace(";", "\\;").replace("#", "\\#")


def export_audiobook(chapters: list, title: str, output_dir: Path, *, author: str = "",
                     config_path: Path | None = None) -> Path:
    """Advance real synthesis then assemble/verify an AAC chaptered M4B.

    Raises AudiobookPending after submitting a batch or observing pending work.
    Retry later with identical arguments. Failed jobs fail closed; no local say
    fallback. Hash-addressed work prevents reuse after text/voice/speed changes.
    WAV frame/item counts, speaking-rate bounds, chunk coverage, final duration
    and chapter count are checked. These detect structural truncation, not every
    conceivable phonetic omission; listening remains an editorial quality gate.
    """
    normalized, settings = _chapters(chapters), _settings(config_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    export_narration_script(normalized, title, output_dir)
    texts, chapter_ranges = [], []
    for chapter in normalized:
        start = len(texts)
        texts.extend(split_narration(chapter.title + ". " + chapter.text))
        chapter_ranges.append((start, len(texts)))
    identity = {"version": 1, "title": title, "author": author, "chapters": [c.__dict__ for c in normalized],
                "voice": settings["voice"], "speed": settings["speed"], "base_url": settings["base_url"]}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    work = output_dir / "audiobook-work" / digest
    work.mkdir(parents=True, exist_ok=True)
    manifest = work / "manifest.json"
    if not manifest.exists():
        _json(manifest, {**identity, "chunks": texts, "sha256": digest})
    paths = [work / f"{index:05d}.wav" for index in range(len(texts))]
    # At most three active jobs: keep the GPU fed without flooding its shared queue.
    # Small batches bound inline base64 result memory and scheduling latency.
    pending, unsubmitted = [], []
    for start in range(0, len(texts), 16):
        indices = list(range(start, min(start + 16, len(texts))))
        batch_file = work / f"batch-{start:05d}.json"
        if all(paths[i].exists() for i in indices):
            for i in indices:
                _wav_info(paths[i])
            continue
        if batch_file.exists():
            job_id = json.loads(batch_file.read_text())["job_id"]
            job = _remote(settings, f"/v1/jobs/{job_id}")
            status = job.get("status")
            if status in {"failed", "cancelled"}:
                raise RuntimeError(f"Remote audiobook job {job_id} {status}; no fallback performed")
            if status != "completed":
                pending.append(job_id)
                continue
            result = job.get("result") or {}
            counts = result.get("item_samples")
            if not isinstance(counts, list) or len(counts) != len(indices) or any(
                not isinstance(n, int) or n <= 0 for n in counts
            ):
                raise ValueError("Remote result omitted or truncated narration items")
            data = base64.b64decode(result["data"], validate=True)
            with wave.open(io.BytesIO(data), "rb") as audio:
                channels, width, rate = audio.getnchannels(), audio.getsampwidth(), audio.getframerate()
                gap = int(result.get("gap_samples", 0))
                minimum = sum(counts) + gap * (len(counts) - 1)
                if audio.getnframes() not in {minimum, minimum + gap}:
                    raise ValueError("Remote result frame coverage mismatch")
                frames = audio.readframes(audio.getnframes())
                if len(frames) != audio.getnframes() * channels * width:
                    raise ValueError("Remote result WAV is truncated")
            offset = 0
            for i, count in zip(indices, counts):
                duration = count / rate
                words = len(texts[i].split())
                # Broad hard bounds catch near-empty output and runaway repeats.
                if duration < max(0.2, words / 7.5) or duration > max(20, words * 2):
                    raise ValueError(f"Implausible narration duration for chunk {i}: {duration:.2f}s")
                target = io.BytesIO()
                with wave.open(target, "wb") as audio:
                    audio.setparams((channels, width, rate, 0, "NONE", "not compressed"))
                    audio.writeframes(frames[offset * channels * width:(offset + count) * channels * width])
                _atomic(paths[i], target.getvalue())
                offset += count + gap
        else:
            unsubmitted.append((batch_file, indices))
    # Inspect every existing job BEFORE filling vacancies. This also handles
    # noncontiguous checkpoints without exceeding the shared GPU queue window.
    for batch_file, indices in unsubmitted:
        if not _synthesis_capacity(pending):
            break
        job = _remote(settings, "/v1/jobs", {"type": "tts-kokoro", "who": "noveliser2",
            "why": "Full unabridged audiobook narration", "params": {
                "items": [{"text": texts[i], "voice": settings["voice"], "speed": float(settings["speed"])}
                          for i in indices], "gap_seconds": 0.0, "force": True}})
        job_id = job["job_id"]
        _json(batch_file, {"job_id": job_id, "indices": indices})
        pending.append(job_id)
    if pending:
        raise AudiobookPending(pending[0])
    infos = [_wav_info(path) for path in paths]
    if len({info[:3] for info in infos}) != 1:
        raise ValueError("Inconsistent synthesis audio format")
    # Stream PCM into one WAV: no thousands-of-inputs ffmpeg command line.
    combined = work / "complete.wav"
    with wave.open(str(combined), "wb") as audio:
        audio.setparams((*infos[0][:3], 0, "NONE", "not compressed"))
        for path in paths:
            with wave.open(str(path), "rb") as source:
                while block := source.readframes(65536):
                    audio.writeframesraw(block)
    durations = [info[3] / info[2] for info in infos]
    metadata = [";FFMETADATA1", f"title={_escape_meta(title)}", f"artist={_escape_meta(author)}", "media_type=2"]
    cursor = 0
    chapter_info = []
    for chapter, (start, end) in zip(normalized, chapter_ranges):
        finish = cursor + sum(durations[start:end])
        chapter_info.append({"title": chapter.title, "start": cursor, "end": finish})
        metadata.extend(["[CHAPTER]", "TIMEBASE=1/1000", f"START={round(cursor * 1000)}",
                         f"END={round(finish * 1000)}", f"title={_escape_meta(chapter.title)}"])
        cursor = finish
    meta_path = work / "chapters.ffmeta"
    meta_path.write_text("\n".join(metadata) + "\n", encoding="utf-8")
    target = output_dir / f"{_safe_title(title)}.m4b"
    temporary = work / "encoded.m4b"
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(combined), "-i", str(meta_path),
          "-map", "0:a:0", "-map_metadata", "1", "-map_chapters", "1", "-c:a", "aac", "-b:a", "96k",
          "-movflags", "+faststart", "-f", "mp4", str(temporary)])
    probe = json.loads(_run(["ffprobe", "-v", "error", "-show_format", "-show_chapters", "-show_streams",
                             "-of", "json", str(temporary)]))
    actual = float(probe["format"]["duration"])
    if not math.isfinite(actual) or abs(actual - cursor) > 0.3 or len(probe["chapters"]) != len(normalized):
        raise ValueError("M4B duration/chapter verification failed")
    if not any(stream.get("codec_name") == "aac" for stream in probe["streams"]):
        raise ValueError("M4B missing AAC audio")
    for expected, actual_chapter in zip(chapter_info, probe["chapters"]):
        if (actual_chapter.get("tags", {}).get("title") != expected["title"]
                or abs(float(actual_chapter["start_time"]) - expected["start"]) > 0.01
                or abs(float(actual_chapter["end_time"]) - expected["end"]) > 0.01):
            raise ValueError("M4B chapter title/timing verification failed")
    _run(["ffmpeg", "-v", "error", "-i", str(temporary), "-f", "null", "-"])
    _atomic(target, temporary.read_bytes())
    _json(output_dir / f"{_safe_title(title)}.audiobook.json", {
        "engine": "remote arbiter tts-kokoro", "voice": settings["voice"], "speed": settings["speed"],
        "source_sha256": digest, "chunks": len(texts), "words": sum(len(t.split()) for t in texts),
        "duration_seconds": cursor, "chapters": chapter_info,
        "audio_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "validation": "complete input coverage, per-item frames/duration, AAC decode and chapter timing",
    })
    return target
