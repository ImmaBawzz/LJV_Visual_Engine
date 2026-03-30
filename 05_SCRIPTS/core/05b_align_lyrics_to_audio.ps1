$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$venvDir = Join-Path $root ".venv-align310"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
$alignerScript = Join-Path $PSScriptRoot "06_align_lyrics_to_audio.py"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.10 to run lyric alignment."
}

if (-not (Test-Path $pythonExe)) {
    Write-Host "Creating lyric-alignment Python 3.10 environment..." -ForegroundColor Cyan
    & py -3.10 -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Python 3.10 environment for lyric alignment."
    }
}

$packagesReady = $true
& $pythonExe -m pip show openai-whisper rapidfuzz torch *> $null
if ($LASTEXITCODE -ne 0) {
    $packagesReady = $false
}

if (-not $packagesReady) {
    Write-Host "Installing lyric-alignment dependencies..." -ForegroundColor Cyan
    & $pythonExe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install torch for lyric alignment."
    }

    & $pythonExe -m pip install openai-whisper rapidfuzz
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install lyric-alignment Python packages."
    }
}

Write-Host "Running audio-based lyric alignment..." -ForegroundColor Cyan
& $pythonExe -u $alignerScript --model small.en --search-ahead 220 --min-score 72
if ($LASTEXITCODE -ne 0) {
    throw "Lyric alignment failed."
}
