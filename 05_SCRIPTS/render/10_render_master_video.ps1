$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$paths = Get-Content (Join-Path $root "01_CONFIG\paths_config.json") -Raw | ConvertFrom-Json
$exports = Get-Content (Join-Path $root "01_CONFIG\export_presets.json") -Raw | ConvertFrom-Json
$project = Get-Content (Join-Path $root "01_CONFIG\project_config.json") -Raw | ConvertFrom-Json
$ffmpeg = $paths.ffmpeg
$primary = $project.primary_format
if (-not $primary) { $primary = "youtube_16x9" }
$targetFps = [int]$exports.$primary.fps
if (-not $targetFps) { $targetFps = 30 }

$audio = Join-Path $root "02_INPUT\audio\song.wav"
$manifest = Join-Path $root "03_WORK\sections\timeline_manifest.json"
$sectionsDir = Join-Path $root "03_WORK\sections"
$tempDir = Join-Path $root "03_WORK\temp"
$outClean = Join-Path $root "04_OUTPUT\youtube_16x9\master_clean.mp4"
$concatFile = Join-Path $tempDir "concat_sections.txt"

New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
if(-not (Test-Path $audio)){ throw "song.wav missing" }
if(-not (Test-Path $manifest)){ throw "timeline_manifest.json missing." }

$manifestJson = Get-Content $manifest -Raw | ConvertFrom-Json
$concatLines = @()

foreach($section in $manifestJson.sections){
    $source = $section.source
    $duration = [double]$section.duration_sec
    $outfile = Join-Path $sectionsDir ($section.output_name)

    & $ffmpeg -y -stream_loop -1 -i $source -t $duration -an -r $targetFps -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p $outfile
    if($LASTEXITCODE -ne 0){ throw "Failed rendering section $($section.label)" }

    $concatLines += "file '$((Resolve-Path $outfile).Path.Replace("'", "''"))'"
}

$concatLines | Set-Content -Encoding Ascii $concatFile

& $ffmpeg -y -f concat -safe 0 -i $concatFile -i $audio -shortest -r $targetFps -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -c:a aac -b:a 320k $outClean
if($LASTEXITCODE -ne 0){ throw "Concat master render failed." }

powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "10b_enhance_master.ps1")
powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "11_burn_lyrics.ps1")
powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "12_mux_softsubs.ps1")
Write-Host "Master timeline render complete."
