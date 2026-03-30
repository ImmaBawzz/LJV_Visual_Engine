# LJV Visual Engine — RELEASE Package

This is the consolidated release-grade delivery scaffold.

## Core promise
If you provide:
- `02_INPUT/audio/song.wav`
- `02_INPUT/video/clip.mp4`
- `02_INPUT/lyrics/lyrics_raw.txt`

this package can produce:
- `master_clean.mp4` with music
- `master_lyrics.mp4` with music + burned-in lyrics
- soft subtitle master
- vertical export
- square export
- teaser cuts
- delivery manifest
- release readiness report

## Main one-click entry
Double-click:
- `05_SCRIPTS/run_release_pipeline.bat`

## NEW: Resumable Pipeline with Checkpoints 🔄
The pipeline now supports **resume from failure** — no more 4-hour restarts on single errors:

```batch
run_release_pipeline.bat           # Run normally
run_release_pipeline.bat resume    # Resume from last failure
run_release_pipeline.bat force     # Force restart (clear checkpoint)
run_release_pipeline.bat status    # Check progress
```

See [CHECKPOINT_GUIDE.md](../09_DOCS/CHECKPOINT_GUIDE.md) for details.

## NEW: Phase 2 Validation + Auto QA Gate
The pipeline now includes fail-fast validation and automatic quality checks:

- Preflight validation report: `03_WORK/reports/preflight_validation_report.json`
- Post-render QA gate report: `03_WORK/reports/quality_gate_report.json`
- Consolidated readiness report: `03_WORK/reports/release_readiness_report.json`

If validation or QA fails, the pipeline stops with actionable errors and can be resumed after fixes.

## Release philosophy
Generation is separated from assembly.
ComfyUI generates source clips.
This package turns those clips into stable deliverables.
