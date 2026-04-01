# LJV Visual Engine — Python Dependencies

## Primary Environment (Python 3.14, workspace venv)

These are for general utility scripts:

```
opencv-python>=4.8.0
numpy>=1.24.0
pillow>=10.0.0
fastapi>=0.115.0
uvicorn>=0.30.0
```

### Authentication & Database (Added for auth dashboard)

```
sqlalchemy>=2.0.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
email-validator>=2.0.0
```

**Optional (for Google OAuth):**
```
authlib>=1.3.0
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
```

## Audio Alignment Environment (Python 3.10, auto-provisioned)

These are for Whisper-based lyric transcription and alignment:

```
torch>=2.0.0          # CPU version sufficient; GPU optional
openai-whisper>=20250625
rapidfuzz>=3.14.0
```

## System-Level Dependencies

- **FFmpeg 4.4+** — Media processing (audio/video encoding, demuxing)
  - Install: `choco install ffmpeg` (Windows) or `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux)
  
- **Python 3.10+** — Runtime environment
  - Install: https://www.python.org/downloads/

- **PowerShell 7.6+** — Pipeline orchestration (Windows)
  - Install: https://github.com/PowerShell/PowerShell/releases

## Installation

### Quick Start (Automatic)

The pipeline bootstraps its own Python 3.10 environment:

```powershell
cd 05_SCRIPTS
.\run_release_pipeline_resumable.ps1
```

First run will install alignment dependencies automatically.

### Manual Setup

```powershell
# Set up primary workspace environment
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip wheel
pip install opencv-python numpy pillow

# Set up alignment environment (Python 3.10)
py -3.10 -m venv .venv-align310
.venv-align310\Scripts\Activate.ps1
pip install --upgrade pip wheel
pip install torch openai-whisper rapidfuzz
```

## Troubleshooting

**ModuleNotFoundError: No module named 'whisper'**
- The alignment environment may not have been created. Delete `.venv-align310/` and re-run the pipeline.

**torch installation hangs or fails**
- Try installing CPU-only variant: `pip install torch --index-url https://download.pytorch.org/whl/cpu`

**FFmpeg not found**
- Ensure FFmpeg is in PATH: `ffmpeg -version`
- On Windows, add FFmpeg `bin/` directory to system PATH, then restart PowerShell

**Python 3.10 not found**
- Install from https://www.python.org/downloads/
- Verify: `py -3.10 --version`
