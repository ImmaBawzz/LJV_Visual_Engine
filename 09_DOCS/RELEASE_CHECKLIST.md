# Release Checklist

## Inputs
- [ ] song.wav present
- [ ] clip.mp4 present
- [ ] lyrics_raw.txt present
- [ ] artist_name.txt present
- [ ] title.txt present

## Config
- [ ] paths_config.json correct
- [ ] project_config.json correct
- [ ] schema validation report PASS (03_WORK/reports/schema_validation_report.json)
- [ ] export presets reviewed
- [ ] lyric style preset chosen

## Reliability tests
- [ ] test_schema_and_failfast.py passes
- [ ] test_checkpoint.py passes

## Rendering
- [ ] master_clean.mp4 created
- [ ] master_lyrics.mp4 created
- [ ] master_softsubs.mp4 created
- [ ] vertical_lyrics.mp4 created
- [ ] square_lyrics.mp4 created
- [ ] teasers created

## Quality
- [ ] lyrics readable
- [ ] audio synced
- [ ] no overlapping lyric cues in lyrics_timed.srt
- [ ] cue duration passes the configured lyric_timing_qc thresholds in 01_CONFIG/project_config.json
- [ ] lyric density passes the configured lyric_timing_qc thresholds in 01_CONFIG/project_config.json
- [ ] subtitle layout passes the configured lyric_timing_qc thresholds in 01_CONFIG/project_config.json
- [ ] alignment diagnostics pass the configured lyric_timing_qc thresholds in 01_CONFIG/project_config.json
- [ ] no missing audio in final exports
- [ ] no broken subtitle path issues
- [ ] no harsh visible loop jump
- [ ] title cards acceptable

## Release bundle
- [ ] delivery manifest written
- [ ] release report written
- [ ] final bundle assembled
- [ ] archive copy saved

## Dashboard ops (Phase 2)
- [ ] dashboard launches on localhost and API health is OK
- [ ] live step status and logs update during a run
- [ ] start/resume/retry controls are disabled while run is active
