# LJV Visual Engine

A professional-grade audio-reactive lyric visualization pipeline for producing high-quality music video assets.

## Overview

LJV Visual Engine transforms raw audio, video clips, and lyric text into production-ready deliverables including:

- **Master videos** with embedded audio and optional burned-in lyrics
- **Soft-subtitle versions** for platform distribution
- **Social exports** (vertical 9×16, square 1×1)
- **QA reports** and delivery manifests
- **Checkpoint recovery** for resumable pipeline execution

All timing is audio-aligned using automated speech recognition, ensuring lyric cues match vocal entries precisely.

## Key Features

✨ **Audio-Aligned Timings**  
Uses OpenAI Whisper for word-level transcription, then fuzzy-matches lyrics to create pixel-perfect cue timing.

🔄 **Resumable Pipeline**  
Built-in checkpointing means pipeline failures don't reset hours of work. Resume from the exact failure point.

✅ **Automated QA**  
Preflight validation + post-render quality gates catch issues early before final export.

🎯 **Modular Workflow**  
Each stage (preparation, loop building, alignment, rendering, release) is independently executable.

📊 **Production Reports**  
Generates alignment diagnostics, quality scorecards, and delivery manifests for transparency and compliance.

## Preview

For a public demo GIF, export a short muted clip from a non-private render with:

```powershell
powershell -ExecutionPolicy Bypass -File .\05_SCRIPTS\tools\02_export_readme_preview_gif.ps1 -SourceVideo ".\04_OUTPUT\youtube_16x9\master_lyrics.mp4"
```

The script writes the preview to `.github/assets/readme-preview.gif`, ready to be committed once you are happy the clip is safe for public release.

## Quick Start

### Requirements

- **Windows 10+** with PowerShell
- **FFmpeg** (4.4+) and **Python 3.10+**
- **Input files**: audio (`.wav`), video (`.mp4`), lyrics (`.txt`)

### Setup

1. Clone this repository
2. Optionally prefill required text inputs:

```powershell
powershell -ExecutionPolicy Bypass -File .\05_SCRIPTS\tools\01_bootstrap_text_inputs.ps1
```

3. Place your media files in the scaffolded `02_INPUT/` subdirectories
4. Review configuration in `01_CONFIG/`
5. Run the pipeline:

If `ffmpeg` or `ffprobe` are not on your system `PATH`, set absolute paths for them in `01_CONFIG/paths_config.json` before running.

```powershell
.\run_release_pipeline.bat
```

For detailed usage and recovery steps, see [QUICKSTART.md](./00_README/QUICKSTART.md) and [CHECKPOINT_GUIDE.md](./09_DOCS/CHECKPOINT_GUIDE.md).

## Documentation

- **[QUICKSTART](./00_README/QUICKSTART.md)** — Five-minute overview
- **[OPERATING MODEL](./09_DOCS/OPERATING_MODEL.md)** — Architecture and design rationale
- **[CHECKPOINT GUIDE](./09_DOCS/CHECKPOINT_GUIDE.md)** — Recovery and resume workflows
- **[RELEASE CHECKLIST](./09_DOCS/RELEASE_CHECKLIST.md)** — Pre-delivery validation steps

## Core Modules

### `05_SCRIPTS/core/`

Core pipeline orchestration:
- **01_validate_environment.ps1** — Verify runtime dependencies
- **02_prepare_inputs.py** — Normalize and validate input files
- **05_generate_ass_from_txt.py** — Generate ASS subtitle files from timing data
- **06_align_lyrics_to_audio.py** — Audio-based lyric timing using Whisper + fuzzy matching
- **08_build_title_cards.py** — Render title sequence graphics
- **09_build_sections.py** — Timeline sectioning and automation

### `05_SCRIPTS/analysis/`

Audio and video analysis:
- **13_audio_reactive_pass.py** — Extract beat and envelope information
- **14_build_simple_beatmap.py** — Create beatmap for timing-driven effects
- **15_build_timeline_manifest.py** — Generate section metadata

### `05_SCRIPTS/render/`

Video rendering and encoding:
- **10_render_master_video.ps1** — Primary video composite
- **11_burn_lyrics.ps1** — Render with burned-in lyrics overlay
- **12_mux_softsubs.ps1** — Embed soft subtitles

### `05_SCRIPTS/release/`

Quality assurance and delivery:
- **16_run_quality_gate.py** — Automated QA scoring
- **17_write_release_report.py** — Consolidated readiness report
- **18_build_release_bundle.py** — Package final deliverables

### `05_SCRIPTS/social/`

Social media and promotional exports:
- **12_render_social_exports.ps1** — Vertical and square format rendering
- **13_render_teasers.py** — Short-form teaser generation

## Configuration

See `01_CONFIG/` for customizable presets:

- `project_config.json` — Project metadata and output paths
- `paths_config.json` — Runtime tool paths and font defaults
- `lyric_style_presets.json` — ASS subtitle styling
- `reactive_presets.json` — Audio analysis parameters
- `export_presets.json` — Encoding and delivery formats

## Pipeline States & Recovery

The pipeline tracks progress in `03_WORK/pipeline_checkpoint.json`. Resume capabilities:

```bash
ps1> .\run_release_pipeline_resumable.ps1              # Continue from last
ps1> .\run_release_pipeline_resumable.ps1 resume       # Explicit resume
ps1> .\run_release_pipeline_resumable.ps1 force        # Clear checkpoint, restart
ps1> .\run_release_pipeline_resumable.ps1 status       # Print current state
```

## Example Output

Running the pipeline produces:

```
04_OUTPUT/
├── youtube_16x9/
│   ├── master_clean.mp4          # Audio + video
│   ├── master_lyrics.mp4         # Audio + video + burned subtitles
│   └── master_softsubs.mp4       # Audio + video + soft subtitles
├── vertical_9x16/                # Mobile-optimized variants
├── square_1x1/                   # Social media squares
├── teasers/                      # Short-form clips
└── delivery_manifest.json        # Asset inventory

03_WORK/reports/
├── preflight_validation_report.json
├── quality_gate_report.json
└── release_readiness_report.json
```

## Lyrics & Timing

Timing data lives in `02_INPUT/lyrics/`:

- **lyrics_raw.txt** — Source text (one line per cue)
- **lyrics_timed.srt** — SRT with automated audio-aligned timings
- **lyrics_styled.ass** — ASS with styling and colors

The alignment system:
1. Transcribes audio with word-level timestamps (Whisper)
2. Fuzzy-matches lyric lines to transcript  
3. Extracts start/end times for each cue
4. Enforces monotonic timing (no overlaps, no rewinds)
5. Outputs SRT + JSON diagnostics

See `03_WORK/analysis/lyrics_alignment_report.json` for full alignment traceability and confidence scores.

## Contributing

This is a release-grade engine designed for professional use. Issues and feature requests are welcome.

For development or local testing:

1. Read [OPERATING_MODEL.md](./09_DOCS/OPERATING_MODEL.md) for architecture
2. Inspect Python environment requirements in `requirements.txt` (if present) or script headers
3. Test incrementally with a small input (30-second sample) before full runs
4. Check `03_WORK/logs/pipeline_execution.json` for execution traces

## License

See LICENSE file (if applicable to your use case).

## Support

- Check [CHECKPOINT_GUIDE.md](./09_DOCS/CHECKPOINT_GUIDE.md) for common recovery patterns
- Review [RELEASE_CHECKLIST.md](./09_DOCS/RELEASE_CHECKLIST.md) before deployment
- Inspect JSON reports in `03_WORK/reports/` for detailed diagnostics

---

**LJV Visual Engine** © 2024+
