from __future__ import annotations

import argparse
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_YOUTUBE_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
    }
)
MODEL_CHOICES = ("tiny", "base", "small", "medium", "large-v3", "turbo")


@dataclass(frozen=True)
class CaptionWord:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class CaptionCue:
    start: float
    end: float
    text: str


def format_srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def sanitize_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-_")
    return safe[:80] or "transcript"


def validate_youtube_url(value: str) -> str:
    parsed = urlparse(value)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or hostname not in ALLOWED_YOUTUBE_HOSTS:
        raise ValueError("Remote sources must be HTTPS URLs on an allowed YouTube hostname")
    if parsed.username or parsed.password or parsed.port:
        raise ValueError("Credentials and custom ports are not allowed in source URLs")
    return value


def group_words(words: list[CaptionWord], max_words: int) -> list[CaptionCue]:
    if max_words < 1:
        raise ValueError("max_words must be at least 1")

    cues: list[CaptionCue] = []
    current: list[CaptionWord] = []
    for word in words:
        current.append(word)
        sentence_end = bool(re.search(r"[.!?]$", word.text.strip()))
        if len(current) >= max_words or (sentence_end and len(current) >= 4):
            cues.append(_cue_from_words(current))
            current = []
    if current:
        cues.append(_cue_from_words(current))
    return cues


def _cue_from_words(words: list[CaptionWord]) -> CaptionCue:
    text = "".join(word.text for word in words).strip()
    return CaptionCue(start=words[0].start, end=words[-1].end, text=text)


def write_outputs(cues: list[CaptionCue], output_dir: Path, name: str, language: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_output = output_dir.resolve()
    base_name = f"{sanitize_name(name)}.{sanitize_name(language)}"
    srt_path = (resolved_output / f"{base_name}.srt").resolve()
    txt_path = (resolved_output / f"{base_name}.txt").resolve()
    if srt_path.parent != resolved_output or txt_path.parent != resolved_output:
        raise ValueError("Output path escaped the selected output directory")

    srt_lines: list[str] = []
    txt_lines: list[str] = []
    for index, cue in enumerate(cues, 1):
        srt_lines.extend(
            [
                str(index),
                f"{format_srt_time(cue.start)} --> {format_srt_time(cue.end)}",
                cue.text,
                "",
            ]
        )
        timestamp = format_srt_time(cue.start).replace(",", ".")
        txt_lines.append(f"[{timestamp}] {cue.text}")

    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    txt_path.write_text("\n".join(txt_lines) + "\n", encoding="utf-8")
    print(f"Created {srt_path}")
    print(f"Created {txt_path}")


def download_youtube_audio(url: str, temporary_dir: Path) -> tuple[Path, str]:
    from yt_dlp import YoutubeDL

    options = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "outtmpl": str(temporary_dir / "source.%(ext)s"),
        "restrictfilenames": True,
    }
    with YoutubeDL(options) as downloader:
        info = downloader.extract_info(validate_youtube_url(url), download=True)
        if info.get("_type") == "playlist" or info.get("entries"):
            raise ValueError("Playlists are not supported")
        prepared = Path(downloader.prepare_filename(info))

    if not prepared.is_file() or prepared.parent.resolve() != temporary_dir.resolve():
        raise RuntimeError("The expected downloaded audio file was not created")
    return prepared, sanitize_name(str(info.get("id") or "youtube-video"))


def transcribe(
    audio_path: Path,
    model_name: str,
    language: str,
    batch_size: int,
    beam_size: int,
    max_words: int,
) -> list[CaptionCue]:
    from faster_whisper import BatchedInferencePipeline, WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    pipeline = BatchedInferencePipeline(model=model)
    segments, _ = pipeline.transcribe(
        str(audio_path),
        language=language,
        batch_size=batch_size,
        beam_size=beam_size,
        vad_filter=True,
        word_timestamps=True,
    )

    words: list[CaptionWord] = []
    fallback_cues: list[CaptionCue] = []
    for segment in segments:
        segment_words = list(segment.words or [])
        if segment_words:
            words.extend(
                CaptionWord(float(word.start), float(word.end), word.word)
                for word in segment_words
                if word.start is not None and word.end is not None and word.word.strip()
            )
        elif segment.text.strip():
            fallback_cues.append(
                CaptionCue(float(segment.start), float(segment.end), segment.text.strip())
            )

    cues = group_words(words, max_words) if words else fallback_cues
    if not cues:
        raise RuntimeError("No speech was transcribed from the input")
    return cues


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Indonesian TXT and SRT captions from authorized media."
    )
    parser.add_argument("source", help="A local media file or an HTTPS YouTube URL")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--model", choices=MODEL_CHOICES, default="small")
    parser.add_argument("--language", default="id")
    parser.add_argument("--batch-size", type=int, choices=range(1, 33), default=8)
    parser.add_argument("--beam-size", type=int, choices=range(1, 11), default=5)
    parser.add_argument("--max-words", type=int, choices=range(1, 31), default=12)
    parser.add_argument("--keep-audio", action="store_true")
    return parser


def run(args: argparse.Namespace) -> None:
    output_dir = args.output_dir.resolve()
    with tempfile.TemporaryDirectory(prefix="indo-caption-") as temp_name:
        temporary_dir = Path(temp_name).resolve()
        if args.source.startswith(("http://", "https://")):
            audio_path, source_name = download_youtube_audio(args.source, temporary_dir)
            downloaded = True
        else:
            audio_path = Path(args.source).expanduser().resolve(strict=True)
            if not audio_path.is_file():
                raise ValueError("The local source must be a file")
            source_name = sanitize_name(audio_path.stem)
            downloaded = False

        cues = transcribe(
            audio_path,
            args.model,
            args.language,
            args.batch_size,
            args.beam_size,
            args.max_words,
        )
        write_outputs(cues, output_dir, source_name, args.language)

        if downloaded and args.keep_audio:
            output_dir.mkdir(parents=True, exist_ok=True)
            retained = output_dir / f"{source_name}.source{audio_path.suffix.lower()}"
            shutil.copy2(audio_path, retained)
            print(f"Retained authorized source audio at {retained}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        run(args)
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
