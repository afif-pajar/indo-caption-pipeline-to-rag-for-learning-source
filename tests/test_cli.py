from pathlib import Path

import pytest

from indo_caption_pipeline.cli import (
    CaptionCue,
    CaptionWord,
    format_srt_time,
    group_words,
    sanitize_name,
    validate_youtube_url,
    write_outputs,
)


def test_format_srt_time() -> None:
    assert format_srt_time(3_661.234) == "01:01:01,234"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=abc123",
        "https://youtu.be/abc123",
        "https://music.youtube.com/watch?v=abc123",
    ],
)
def test_validate_youtube_url_accepts_allowlist(url: str) -> None:
    assert validate_youtube_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://www.youtube.com/watch?v=abc123",
        "https://youtube.com.example.test/watch?v=abc123",
        "https://example.test/video",
        "https://user:password@youtube.com/watch?v=abc123",
        "https://youtube.com:8443/watch?v=abc123",
    ],
)
def test_validate_youtube_url_rejects_unsafe_sources(url: str) -> None:
    with pytest.raises(ValueError):
        validate_youtube_url(url)


def test_sanitize_name_removes_path_characters() -> None:
    assert sanitize_name("../../A learning source: 01") == "A-learning-source-01"


def test_group_words_respects_word_limit() -> None:
    words = [CaptionWord(float(i), float(i + 1), f" word{i}") for i in range(5)]
    cues = group_words(words, max_words=3)
    assert [cue.text for cue in cues] == ["word0 word1 word2", "word3 word4"]


def test_write_outputs_stays_in_output_directory(tmp_path: Path) -> None:
    write_outputs([CaptionCue(0.0, 1.0, "Halo dunia")], tmp_path, "../unsafe", "id")
    assert (tmp_path / "unsafe.id.srt").is_file()
    assert (tmp_path / "unsafe.id.txt").is_file()

