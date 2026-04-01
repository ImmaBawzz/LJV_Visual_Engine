# Pipeline Checkpoints & Resume Guide

## Overview

The release pipeline now supports **resumable execution** with checkpoints. This means:

- ✅ If a step fails at hour 3 of a 4-hour render, you can resume from that step
- ✅ No loss of already-completed work
- ✅ Detailed logging of what failed and why
- ✅ Progress tracking across runs

## Quick Usage

### Run Pipeline (Default)
```batch
run_release_pipeline.bat
```
This runs from step 1, or resumes if a previous run was interrupted.

### Resume from Last Failure
```batch
run_release_pipeline.bat resume
```
Skips all completed steps, starts from the first failed step. Use this after fixing an error.

### Force Restart
```batch
run_release_pipeline.bat force
```
Clears all checkpoint data and restarts from step 1. Use this before starting a new project.

### Check Status
```batch
run_release_pipeline.bat status
```
Shows detailed checkpoint report with timing and errors.

### View Execution Log
```batch
run_release_pipeline.bat log
```
Shows all pipeline events with timestamps.

### Request Graceful Stop (Fail-Safe)
```batch
run_release_pipeline.bat stop
```
Requests a cooperative halt. The current step is allowed to finish, then the pipeline stops before the next step.

### Request Immediate Emergency Stop (Fail-Safe)
```batch
run_release_pipeline.bat stop --now
```
Requests an emergency halt and attempts to terminate the active pipeline process tree immediately.

### Signed Stop-File Trigger
Create a signed `stop.now` at repository root:

```batch
set LJV_STOP_SECRET=your_shared_secret_here
python 05_SCRIPTS\tools\stop_control.py create --mode graceful --reason "Operator requested stop"
```

For immediate halt:

```batch
set LJV_STOP_SECRET=your_shared_secret_here
python 05_SCRIPTS\tools\stop_control.py create --mode immediate --reason "Emergency stop"
```

The runner validates the HMAC signature before halting. Invalid or expired signatures are ignored.
Default max signature age is 1800 seconds and can be changed via `LJV_STOP_SIG_MAX_AGE_SEC`.

### Option 2: TOTP + Signed Stop File (Recommended)
Enable a second factor so stop requests require both signature and authenticator code.

1. Generate and store secrets once:

```batch
python 05_SCRIPTS\tools\stop_control.py gen-secret
python 05_SCRIPTS\tools\stop_control.py gen-totp-secret
```

2. Set environment variables for runner and control commands:

```batch
set LJV_STOP_SECRET=your_hmac_secret
set LJV_STOP_TOTP_SECRET=your_base32_totp_secret
set LJV_STOP_REQUIRE_TOTP=true
```

3. Create a stop request with current authenticator code:

```batch
python 05_SCRIPTS\tools\stop_control.py create --mode graceful --totp-code 123456 --reason "Operator requested stop"
```

4. Verify stop file (manual check):

```batch
python 05_SCRIPTS\tools\stop_control.py verify --json
```

Notes:
- `run_release_pipeline.bat stop` will prompt for TOTP if `LJV_STOP_TOTP_SECRET` is set and `LJV_STOP_TOTP_CODE` is not provided.
- The TOTP code is validated against the stop file timestamp (with small clock skew tolerance).

### Reset Checkpoint
```batch
run_release_pipeline.bat reset
```
Same as `force`, but without running the pipeline.

---

## How It Works

### Checkpoint File
Located at: `03_WORK/pipeline_checkpoint.json`

Stores:
- Pipeline status (overall) for each run
- Per-step status (pending/running/completed/failed)
- Timing info (start/end time, duration)
- Error messages for failed steps

Example:
```json
{
  "pipeline_version": "1.0",
  "created_at": "2026-03-30T14:22:45.123456",
  "last_updated": "2026-03-30T15:45:12.789012",
  "overall_status": "failed",
  "steps": {
    "1": {
      "name": "Validate Environment",
      "status": "completed",
      "start_time": "2026-03-30T14:22:45.123456",
      "end_time": "2026-03-30T14:22:46.234567",
      "duration_sec": 1.11,
      "exit_code": 0,
      "error": null
    },
    "11": {
      "name": "Render Master Video",
      "status": "failed",
      "start_time": "2026-03-30T15:42:10.123456",
      "end_time": "2026-03-30T15:45:12.789012",
      "duration_sec": 182.67,
      "exit_code": 1,
      "error": "ffmpeg: Codec not found"
    }
  }
}
```

### Structured Log
Located at: `03_WORK/logs/pipeline_execution.json`

Each entry contains:
- Timestamp
- Log level (INFO/WARNING/ERROR)
- Step name
- Message
- Exit code

Use this for debugging and audit trails.

---

## Pipeline Stages

The pipeline has 16 main steps:

| Step | Name | Type | Est. Duration | Depends On |
|------|------|------|---------------|-----------|
| 1 | Validate Environment | Validation | 1-2s | None |
| 2 | Preflight Input Validation | Validation | 1-3s | Config, inputs |
| 3 | Prepare Inputs | Processing | 5-10s | song.wav, clip.mp4 |
| 4 | Build Pingpong Loop | Assembly | 10-30s | clip.mp4 |
| 5 | Build Loop Variants | Processing | 5-10s | Step 4 |
| 6 | Align Lyrics To Audio | Processing | 2-6 min | song.wav, lyrics_raw.txt, Python 3.10 |
| 7 | Generate ASS Subtitles | Processing | 2-5s | Step 6 or lyrics_timed.srt |
| 8 | Build Title Cards | Assembly | 5-10s | Config |
| 9 | Build Sections | Assembly | 10-20s | Config |
| 10 | Audio Reactive Pass | Analysis | 10-20s | song.wav |
| 11 | Build Simple Beatmap | Analysis | 5-10s | Step 10 |
| 12 | Build Timeline Manifest | Assembly | 5-10s | Steps 9, 11 |
| 13 | Render Master Video | Rendering | 1-3 hours | Steps 4-12 |
| 14 | Render Social Exports | Rendering | 30-60 min | Step 13 |
| 15 | Render Teasers | Rendering | 10-20 min | Step 13 |
| 16 | Quality Gate Auto Check | Validation | 1-5s | Render outputs |
| 17 | Write Delivery Manifest | Documentation | 1-2s | Step 15 |
| 18 | Write Release Report | Documentation | 1-2s | All steps |
| 19 | Build Release Bundle | Packaging | 2-5s | All steps |

---

## Error Recovery Workflow

## Halt Recovery Workflow

### Scenario: Operator-triggered stop

1. Request stop:
   ```batch
   run_release_pipeline.bat stop
   ```
   Or emergency stop:
   ```batch
   run_release_pipeline.bat stop --now
   ```

2. Confirm halt state:
   ```batch
   run_release_pipeline.bat status
   ```
   Look for `Overall Status: HALTED` and halt details.

3. Clear halt request before restart:
   ```batch
   python 05_SCRIPTS/core/checkpoint_cli.py clear-halt
   ```
   And remove sentinel file if present:
   ```batch
   del stop.now
   ```

4. Resume from checkpoint:
   ```batch
   run_release_pipeline.bat resume
   ```

---

## Error Recovery Workflow

### Scenario: Render fails at hour 3

1. **Pipeline stops** and checkpoint records the failure
2. **Check status**:
   ```batch
   run_release_pipeline.bat status
   ```
   Output shows:
   ```
   PIPELINE CHECKPOINT REPORT
   Overall Status: FAILED
   [✓] Step 1: Validate Environment...
   [✓] Step 12: Build Timeline Manifest...
   [✗] Step 13: Render Master Video... | ERROR: GPU out of memory
   Can resume from step 13
   ```

3. **Fix the issue**:
   - Example: Increase swap space, close other GPU processes
   - Or: Reduce output quality in config

4. **Resume**:
   ```batch
   run_release_pipeline.bat resume
   ```
   - Steps 1-12 are skipped (already done)
   - Step 13+ execute normally

---

## Common Scenarios

### Scenario A: Transient Error (e.g., network, temporary resource)
1. Run pipeline, it fails at step X
2. Wait a minute, then:
   ```batch
   run_release_pipeline.bat resume
   ```

### Scenario B: Configuration Error
1. Pipeline fails, shows error in checkpoint
2. Fix config (e.g., wrong paths in `paths_config.json`)
3. Resume:
   ```batch
   run_release_pipeline.bat resume
   ```

### Scenario C: Input File Issue
1. Pipeline fails at step 2 (Prepare Inputs)
2. Example: `song.wav` codec not supported
3. Fix: Replace with valid WAV file
4. Resume:
   ```batch
   run_release_pipeline.bat resume
   ```

### Scenario D: Starting a New Project
1. Replace inputs in `02_INPUT/`
2. Update `01_CONFIG/project_config.json`
3. Clear old checkpoint:
   ```batch
   run_release_pipeline.bat force
   ```

---

## Debugging

### View Full Timeline
```batch
run_release_pipeline.bat log
```
Shows all events with timestamps. Useful for:
- Identifying which step took longest
- Finding performance bottlenecks
- Tracing error sequence

### Check Only (Don't Run)
```batch
run_release_pipeline.bat status
```
Shows current state without executing anything.

### Manual Step Restart
If you need to re-run a specific step:
1. Manually delete only that step's outputs
2. Either:
   - Edit `03_WORK/pipeline_checkpoint.json` and mark that step as "pending"
   - Run `run_release_pipeline.bat force` to restart everything

---

## Limitations & Notes

### Checkpoint is Per-Project
Each project must use its own working directory:
- ✅ Good: Project A in `C:\work\project_a`, Project B in `C:\work\project_b`
- ❌ Bad: Reusing same `03_WORK` folder for different projects (checkpoints will conflict)

### Manual Edits Won't Update Checkpoint
If you manually re-run a step outside the pipeline:
- Checkpoint won't auto-update
- Next pipeline run might skip that step (thinking it's done)
- Solution: Edit `pipeline_checkpoint.json` or use `reset`

### Checkpoint File Can Be Deleted
If `03_WORK/pipeline_checkpoint.json` is deleted:
- Pipeline behavior = fresh start (like step 1)
- No harm, just loses resume capability

### Parallel Runs Not Supported
The checkpoint system assumes one pipeline run at a time:
- ❌ Don't: Run two pipelines with same working directory simultaneously
- ✅ Do: Use separate working directories for parallel runs

---

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Run Release Pipeline
  run: |
    cd ${{ github.workspace }}/05_SCRIPTS
    ./run_release_pipeline.bat resume
  continue-on-error: false
```

### Jenkins Example
```groovy
stage('Release Pipeline') {
    steps {
        bat 'cd scripts && run_release_pipeline.bat'
    }
}
```

---

## Advanced: Checkpoint API

For custom scripts that integrate with the pipeline:

```python
from core.checkpoint_manager import get_checkpoint

cp = get_checkpoint()

# At step start
cp.mark_step_started(step_id=17, step_name="Custom Step")

# On success
cp.mark_step_complete(step_id=17, step_name="Custom Step", exit_code=0)

# On failure
cp.mark_step_failed(step_id=17, step_name="Custom Step", exit_code=1, error="Detailed error message")

# Get status
completed = cp.get_completed_steps()  # [1, 2, 3, ...]
resume_point = cp.get_resume_point()  # 11 (next to run)

# Show report
print(cp.report())
```

---

## Troubleshooting

### Q: Checkpoint keeps saying "not found" error
**A:** Check that the script file path in `run_release_pipeline_resumable.ps1` is correct relative to `05_SCRIPTS/`.

### Q: Resume doesn't work, pipeline restarts from step 1
**A:** 
- Option 1: Check if `03_WORK/pipeline_checkpoint.json` exists and is valid
- Option 2: Verify the `--Resume` flag is being passed (case-sensitive)
- Option 3: Run `run_release_pipeline.bat status` to see current state

### Q: Can I resume from a specific step (not the first failed)?
**A:** Currently no, but you can:
1. Edit `pipeline_checkpoint.json` manually, mark steps as "pending"
2. Or use the Python API: `cp.state["steps"][15]["status"] = "pending"`

### Q: Where are my outputs if a step fails?
**A:** They're in their step-specific folder:
- Step 4: `03_WORK/loops/`
- Step 13: `04_OUTPUT/youtube_16x9/master_clean.mp4`
- Etc. (see RELEASE_PLAN.md)

---

## Next Steps for Phase 1

- [ ] Input validation (pre-flight checks before step 1)
- [ ] Structured logging with JSON aggregation  
- [ ] Automated test suite for pipeline recovery

See [HOLLYWOOD_PRODUCTION_AUDIT.md](../OPERATING_MODEL.md) for full Phase 1-4 roadmap.
