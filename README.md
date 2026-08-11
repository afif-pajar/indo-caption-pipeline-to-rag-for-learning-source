# Indonesian Caption Pipeline for RAG Learning Sources

A local-first Python CLI that downloads a single YouTube video's audio, transcribes Indonesian speech with `faster-whisper`, and produces timestamped TXT and SRT files suitable for review and downstream RAG ingestion.

The repository contains source code only. It intentionally excludes downloaded media, generated transcripts, model files, credentials, and material from any particular learning source.

## Responsible use

Only process media that you own or are authorized to download, transcribe, and reuse. A public URL does not automatically grant redistribution rights. Review the source platform's terms and applicable law before processing content. Generated transcripts can contain mistakes and should be proofread before publication or retrieval use.

## Requirements

- Python 3.11 or newer
- Internet access for YouTube downloads and the first model download
- Sufficient free disk space for the selected Whisper model

No system FFmpeg installation is required for ordinary transcription because `faster-whisper` uses PyAV for audio decoding. YouTube extraction behavior can still change upstream.

## Installation

Using `uv`:

```bash
uv sync --locked
```

Using `pip`:

```bash
python -m venv .venv
python -m pip install .
```

## Usage

Transcribe a single YouTube video:

```bash
uv run indo-caption "https://www.youtube.com/watch?v=VIDEO_ID"
```

Transcribe an audio file you already have permission to use:

```bash
uv run indo-caption path/to/audio.mp3 --output-dir outputs
```

Common options:

```text
--model small          Whisper model size
--language id          Spoken-language code
--batch-size 8         Parallel inference batch size
--beam-size 5          Decoding beam size
--max-words 12         Maximum words per SRT cue
--keep-audio           Retain a downloaded audio copy
```

The default output directory is `outputs/`, which is ignored by Git. Output names are sanitized before filesystem use.

## Outputs

- `<source>.id.srt`: readable caption cues using word-level timestamps
- `<source>.id.txt`: timestamped text for review or later chunking
- `<source>.source.<ext>`: optional downloaded audio when `--keep-audio` is set

The TXT file is an intermediate learning-source artifact, not a complete RAG system. Chunking, embedding, metadata enrichment, authorization, deletion, and retrieval evaluation belong in downstream stages.

## Security properties

- Accepts only local files or HTTPS URLs on an explicit YouTube hostname allowlist.
- Rejects playlists and processes one video per invocation.
- Does not invoke a shell with user-controlled input.
- Sanitizes generated filenames and confines outputs to the selected directory.
- Uses a temporary directory for remote audio and deletes it after processing.
- Does not read browser cookies, `.env` files, or authentication tokens.
- Git ignores media, transcripts, environments, model directories, and common secret files.

See [SECURITY.md](SECURITY.md) for vulnerability reporting and [THREAT_MODEL.md](THREAT_MODEL.md) for trust boundaries.

## Development

```bash
uv sync --locked --extra dev
uv run ruff check .
uv run pytest
uv run bandit -q -r src
uv run pip-audit
```

## License

The source code is licensed under the MIT License. This license does not grant rights to third-party media, transcripts, model weights, or service content processed with the tool.
