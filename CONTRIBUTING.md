# Contributing to LJV Visual Engine

[![Good First Issues](https://img.shields.io/github/issues/ImmaBawzz/LJV_Visual_Engine/good%20first%20issue?color=green&logo=github)](https://github.com/ImmaBawzz/LJV_Visual_Engine/issues?q=is%3Aopen+is%3Aissue+label%3A"good+first+issue")
[![Documentation Issues](https://img.shields.io/github/issues/ImmaBawzz/LJV_Visual_Engine/documentation?color=blue&logo=github)](https://github.com/ImmaBawzz/LJV_Visual_Engine/issues?q=is%3Aopen+is%3Aissue+label%3Adocumentation)

Thank you for your interest in contributing! This document outlines guidelines for reporting issues, requesting features, and submitting code changes.

## Quick Links

- 📋 [Issue Tracker](https://github.com/ImmaBawzz/LJV_Visual_Engine/issues)
- 💬 [Discussions](https://github.com/ImmaBawzz/LJV_Visual_Engine/discussions)
- 📖 [Documentation](./09_DOCS/)
- 🎯 [Good First Issues](https://github.com/ImmaBawzz/LJV_Visual_Engine/issues?q=is%3Aopen+is%3Aissue+label%3A"good+first+issue")

## How to Contribute

### 1. Reporting Issues

When reporting a bug, please provide:

1. **Pipeline state** — Output of `run_release_pipeline_resumable.ps1 status`
2. **Error message** — Full text from the terminal or `03_WORK/logs/pipeline_execution.json`
3. **Input details** — Video resolution, audio duration, lyric line count
4. **Environment** — OS, PowerShell version, FFmpeg version, Python version

Example issue template:

```markdown
**Environment:**
- Windows 11, PowerShell 7.6
- FFmpeg 6.0
- Python 3.10 (workspace venv)

**Error:**
```
Step 06: Align Lyrics To Audio
ValueError: Unable to align lyric line 15
Search exhausted at word index 487 (of 553)
```

**Reproduction:**
1. Run with 4m18s audio + 36-line lyric file
2. Pipeline reaches step 6
3. Fails on "I am becoming" line

**Attachment:**
- 03_WORK/analysis/lyrics_alignment_report.json
```

### 2. Feature Requests

Suggest new features by describing:

- **Use case** — Why is this feature needed?
- **Proposed behavior** — How should it work?
- **Impact** — Does it add a new rendering format? Change the pipeline order? Add a new validation gate?

Examples of welcome contributions:

- ✅ New output format support (e.g., `.mov` export)
- ✅ Additional QA metrics or validation checks
- ✅ Configuration presets for common video specs
- ✅ Enhanced dashboard features
- ✅ Additional social media export formats
- ✅ Improved error handling and recovery
- ✅ Performance optimizations (faster Whisper inference, batch processing)
- ✅ Cross-platform support (Linux/macOS bash equivalents)
- ⚠️ Breaking changes to checkpoint format (requires careful migration)

## Code Contributions

### Collaboration Model (Owner + Contributors)

Use this operating model to keep work fast and safe:

1. **Issue first** — Every non-trivial change starts with a GitHub issue
2. **Branch per task** — Use `feature/...`, `fix/...`, or `docs/...` branch names
3. **PR required** — Merge through pull requests only (no direct pushes to `main`)
4. **Evidence required** — PRs must include test and report evidence
5. **Owner review gate** — Owner approval is required before merge

Recommended cadence:

- Open issue with acceptance criteria
- Push small commits daily
- Open draft PR early for visibility
- Finalize PR only after the validation checklist is complete

Merge standards:

- Prefer **Squash and merge** for a clean history
- Delete merged branches
- Link PRs to issues for traceability

### Code Style

**Python:**
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use 4-space indentation
- Add docstrings to all functions and classes
- Keep lines under 100 characters

**PowerShell:**
- Use PascalCase for function names
- Use lowercase for parameters
- Add comment blocks explaining complex operations
- use Set-StrictMode -Version 2.0 for safety

### Adding New Steps to the Pipeline

If you're adding a new processing step:

1. **Create a new script** in the appropriate `05_SCRIPTS/` subdirectory
2. **Add checkpoint support** using `checkpoint_cli.py`:
   ```python
   from checkpoint_cli import checkpoint
   checkpoint.mark_step(step_number, "Step name")
   # ... do work ...
   checkpoint.mark_complete(step_number)
   ```
3. **Generate a status file** for terminal-independent progress:
   ```python
   import json
   status = {"step": "step_name", "status": "complete", "message": "Done"}
   with open("03_WORK/temp/step_status.json", "w") as f:
       json.dump(status, f)
   ```
4. **Update the pipeline** in `run_release_pipeline_resumable.ps1`:
   - Add the new step with correct numbering
   - Preserve checkpoint state
   - Include error handling and retry logic

5. **Test independently** before integration:
   ```bash
   python 05_SCRIPTS/path/to/new_step.py --help
   ```

6. **Document** in appropriate README or guide

### Testing

Before submitting a PR, test with:

- **Small input** (30-second clip, 5–10 lyric lines)
- **Typical input** (4–5 minute song, 30–50 lyric lines)
- **Checkpoint recovery** (interrupt mid-run, resume, verify output)

Test commands:

```powershell
# Full run with clean state
Remove-Item 03_WORK/pipeline_checkpoint.json
.\run_release_pipeline_resumable.ps1

# Resume from a specific step
.\run_release_pipeline_resumable.ps1 resume

# Check output integrity
Get-ChildItem 04_OUTPUT -Recurse | Measure-Object -Sum -Property Length
```

### Documentation

- Update [OPERATING_MODEL.md](./09_DOCS/OPERATING_MODEL.md) if you change architecture
- Update [CHECKPOINT_GUIDE.md](./09_DOCS/CHECKPOINT_GUIDE.md) if you add/modify pipeline steps
- Add inline comments in complex functions
- Include examples in docstrings

### Submitting a Pull Request

1. **Fork and branch** — Create a feature branch: `git checkout -b feature/your-feature-name`
2. **Commit with clear messages** — Reference issues when relevant: `git commit -m "Add X feature (closes #123)"`
3. **Test end-to-end** — Include test results in PR description
4. **Document changes** — Update relevant guides and READMEs
5. **Submit PR** with:

   - Description of what changed and why
   - Test results (input type, output files verified)
   - Any breaking changes or migration steps required

## Development Setup

### Python Dependencies

The pipeline uses separate Python environments:

**Workspace environment (Python 3.14):**
```bash
# For general scripts (existing setup)
pip install opencv-python numpy pillow
```

**Alignment environment (Python 3.10, auto-provisioned):**
```bash
# For Whisper-based lyric alignment (auto-installed by 05b_align_lyrics_to_audio.ps1)
pip install torch openai-whisper rapidfuzz
```

To manually set up the alignment environment:

```powershell
py -3.10 -m venv .venv-align310
.venv-align310\Scripts\Activate.ps1
pip install --upgrade pip wheel
pip install torch openai-whisper rapidfuzz
```

### Local Testing Workflow

```bash
# 1. Prepare a small test clip (30 seconds)
ffmpeg -i input.wav -t 30 test_audio.wav

# 2. Run full pipeline with test inputs
cd 05_SCRIPTS
.\run_release_pipeline_resumable.ps1

# 3. Inspect outputs
ls ../04_OUTPUT/youtube_16x9/

# 4. Check reports
cat ../03_WORK/reports/quality_gate_report.json
```

## Questions?

Check the documentation first:

- [OPERATING_MODEL.md](./09_DOCS/OPERATING_MODEL.md) — Design and workflow
- [CHECKPOINT_GUIDE.md](./09_DOCS/CHECKPOINT_GUIDE.md) — Recovery and resume
- [RELEASE_CHECKLIST.md](./09_DOCS/RELEASE_CHECKLIST.md) — Pre-delivery steps

## AI Agent & Discoverability

This repository is optimized for discovery by both human developers and AI coding agents:

### Structured Metadata

- **JSON-LD Schema**: `.github/metadata.jsonld` provides machine-readable project information
- **Open Graph Tags**: `.github/seo_metadata.html` contains social sharing metadata
- **GitHub Topics**: Repository is tagged with relevant keywords for discovery

### API Access

The repository metadata can be accessed programmatically:

```bash
# GitHub API
curl https://api.github.com/repos/ImmaBawzz/LJV_Visual_Engine

# Local API (when running)
curl http://localhost:8000/repo-info
curl http://localhost:8000/project-info
curl http://localhost:8000/features
```

### Vector Search & Embeddings

README and documentation are indexed daily for semantic search:

- **Embedding Generation**: Automated via GitHub Actions workflow
- **Storage**: Pinecone vector database for fast similarity search
- **Schedule**: Re-indexed at 12:00 AM UTC daily

### Auto-Labeling

Issues are automatically labeled based on content:

- `good first issue` — Beginner-friendly contributions
- `documentation` — Docs-related issues
- `examples` — Template and sample code issues
- `templates` — 06_TEMPLATES directory issues

### Contributing to Discoverability

You can help improve repository discoverability by:

1. **Adding keywords** to README and metadata files
2. **Writing clear issue descriptions** with relevant technical terms
3. **Creating example scripts** in `examples/` or `06_TEMPLATES/`
4. **Updating documentation** with usage patterns
5. **Adding schema validation** for new configuration files

## Code of Conduct

Please be respectful and constructive in all interactions. No discrimination, harassment, or abuse is tolerated.

---

Thank you for contributing! 🙌
