$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$paths = Get-Content (Join-Path $root "01_CONFIG\paths_config.json") -Raw | ConvertFrom-Json
$ffmpeg = $paths.ffmpeg
$src = Join-Path $root "04_OUTPUT\youtube_16x9\master_lyrics.mp4"
$vertical = Join-Path $root "04_OUTPUT\vertical_9x16\vertical_lyrics.mp4"
$square = Join-Path $root "04_OUTPUT\square_1x1\square_lyrics.mp4"
& $ffmpeg -y -i $src -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" -c:v libx264 -preset medium -crf 20 -c:a copy $vertical
if($LASTEXITCODE -ne 0){ throw "Vertical export failed." }
& $ffmpeg -y -i $src -vf "scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080" -c:v libx264 -preset medium -crf 20 -c:a copy $square
if($LASTEXITCODE -ne 0){ throw "Square export failed." }
Write-Host "Social exports complete."
