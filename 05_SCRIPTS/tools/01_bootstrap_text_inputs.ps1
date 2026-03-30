$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$templateDir = Join-Path $root "06_TEMPLATES\text"
$targetFiles = @(
    @{ Template = Join-Path $templateDir "artist_name.example.txt"; Target = Join-Path $root "02_INPUT\branding\artist_name.txt" },
    @{ Template = Join-Path $templateDir "title.example.txt"; Target = Join-Path $root "02_INPUT\branding\title.txt" },
    @{ Template = Join-Path $templateDir "lyrics_raw.example.txt"; Target = Join-Path $root "02_INPUT\lyrics\lyrics_raw.txt" }
)

foreach ($item in $targetFiles) {
    $targetDir = Split-Path -Parent $item.Target
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

    if (Test-Path $item.Target) {
        Write-Host "SKIP  $($item.Target) already exists"
        continue
    }

    if (-not (Test-Path $item.Template)) {
        throw "Missing template: $($item.Template)"
    }

    Copy-Item $item.Template $item.Target
    Write-Host "WRITE $($item.Target)"
}

Write-Host ""
Write-Host "Text bootstrap complete."
Write-Host "Add your media files manually:"
Write-Host "- 02_INPUT/audio/song.wav"
Write-Host "- 02_INPUT/video/clip.mp4"
