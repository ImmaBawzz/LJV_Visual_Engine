# Quickstart

## 1. Configure paths
Edit:
- `01_CONFIG/paths_config.json`

Defaults assume `ffmpeg` and `ffprobe` are available on your system `PATH`.
If they are not, replace those values with absolute executable paths in `01_CONFIG/paths_config.json`.

## 2. Drop inputs
Optional bootstrap for required text files:

```powershell
powershell -ExecutionPolicy Bypass -File .\05_SCRIPTS\tools\01_bootstrap_text_inputs.ps1
```

Place:
- `song.wav` in `02_INPUT/audio/`
- `clip.mp4` in `02_INPUT/video/`
- lyrics in `02_INPUT/lyrics/lyrics_raw.txt`

The pipeline now performs audio-based lyric alignment automatically and writes strict timings to `02_INPUT/lyrics/lyrics_timed.srt` before generating `lyrics_styled.ass`.

If you already have hand-timed subtitles, you can still edit `02_INPUT/lyrics/lyrics_timed.srt` directly and rerun subtitle generation to preserve those exact cue times.

## 3. Optional: Enable phone notifications
You can get live updates on your phone for start/progress/failure/success events.

### Option A: ntfy (fastest setup)
Install the **ntfy** app on your phone and subscribe to a topic (example: `ljv-release-shadow`).

In the same PowerShell session where you run the pipeline:

```powershell
$env:LJV_NOTIFY_CHANNEL = "ntfy"
$env:LJV_NOTIFY_NTFY_TOPIC = "ljv-release-shadow"
$env:LJV_NOTIFY_TITLE = "LJV Release"
```

Optional custom server:

```powershell
$env:LJV_NOTIFY_NTFY_SERVER = "https://ntfy.sh"
```

### Option B: Discord or Slack webhook
Set your incoming webhook URL:

```powershell
$env:LJV_NOTIFY_CHANNEL = "discord"   # or "slack"
$env:LJV_NOTIFY_WEBHOOK_URL = "https://..."
$env:LJV_NOTIFY_TITLE = "LJV Release"
```

### Option C: Generic webhook

```powershell
$env:LJV_NOTIFY_CHANNEL = "webhook"
$env:LJV_NOTIFY_WEBHOOK_URL = "https://your-endpoint.example.com/hooks/pipeline"
```

## 4. Run the release pipeline
Double-click or command line:
- `run_release_pipeline.bat`

Options:
```batch
run_release_pipeline.bat           # Normal run (or resume if interrupted)
run_release_pipeline.bat resume    # Resume from last failure
run_release_pipeline.bat force     # Force restart from step 1
run_release_pipeline.bat status    # Check pipeline progress
run_release_pipeline.bat log       # View execution log
```

## 5. If pipeline fails
The pipeline auto-saves progress. To resume from where it failed:
```batch
run_release_pipeline.bat resume
```

This skips already-completed steps and continues from the first failure.

For details, see [CHECKPOINT_GUIDE.md](../09_DOCS/CHECKPOINT_GUIDE.md).

## 6. Review validation and QA reports
After (or during) a run, check:
- `03_WORK/reports/preflight_validation_report.json`
- `03_WORK/reports/schema_validation_report.json`
- `03_WORK/reports/quality_gate_report.json`
- `03_WORK/reports/release_readiness_report.json`

The pipeline now fails fast when preflight validation or quality gate checks fail.

The repo keeps `02_INPUT/`, `03_WORK/`, and `04_OUTPUT/` as empty tracked scaffolds. Your actual media, reports, and renders stay ignored by git.

## 7. Run reliability tests (recommended)
Run these before major config or pipeline edits:

```powershell
c:/Users/Shadow/Downloads/LJV_Visual_Engine_RELEASE_Package/.venv/Scripts/python.exe 05_SCRIPTS/core/test_schema_and_failfast.py
c:/Users/Shadow/Downloads/LJV_Visual_Engine_RELEASE_Package/.venv/Scripts/python.exe 05_SCRIPTS/core/test_checkpoint.py
```

## 8. Final outputs
Check:
- `04_OUTPUT/youtube_16x9/master_clean.mp4`
- `04_OUTPUT/youtube_16x9/master_lyrics.mp4`
- `04_OUTPUT/youtube_16x9/master_softsubs.mp4`
- `04_OUTPUT/vertical_9x16/vertical_lyrics.mp4`
- `04_OUTPUT/square_1x1/square_lyrics.mp4`
- `04_OUTPUT/teasers/`
- `04_OUTPUT/release_bundle/`
