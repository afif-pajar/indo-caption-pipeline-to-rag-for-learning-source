# Threat Model

## Assets

- Local media and generated transcripts
- Files in the selected output directory
- Developer credentials and GitHub workflow tokens
- Availability of the machine running transcription

## Trust boundaries

- YouTube pages and downloaded media are untrusted network input.
- Model and Python packages are third-party supply-chain inputs.
- Local input files may be malformed or adversarial.
- Generated transcripts are untrusted text when later inserted into databases, prompts, HTML, or search indexes.

## Controls

- Remote sources are restricted to HTTPS and an explicit YouTube hostname allowlist.
- Playlist downloads are disabled.
- User input is passed through Python APIs rather than shell interpolation.
- Output names are sanitized and resolved under a caller-selected output directory.
- Remote audio is stored in a temporary directory and removed by default.
- Repository rules exclude media, generated transcripts, secrets, model data, and virtual environments.
- CI receives read-only repository permissions and no application secrets.
- Dependencies are locked and monitored by Dependabot.

## Residual risks

- Upstream extractors, decoders, model loaders, and model files can contain vulnerabilities.
- A long or crafted input can consume excessive CPU, memory, disk, or network bandwidth.
- Platform terms or media licenses can prohibit a technically successful download.
- Transcripts can contain hallucinations, personal data, harmful text, or prompt-injection strings.
- Downstream RAG systems must treat transcript contents as data, not instructions.

