$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$paths = Get-Content (Join-Path $root "01_CONFIG\paths_config.json") -Raw | ConvertFrom-Json
$exports = Get-Content (Join-Path $root "01_CONFIG\export_presets.json") -Raw | ConvertFrom-Json
$project = Get-Content (Join-Path $root "01_CONFIG\project_config.json") -Raw | ConvertFrom-Json
$ffmpeg = $paths.ffmpeg

$enabled = $project.enhancement.enabled -eq $true
if (-not $enabled) {
    Write-Host "Enhancement disabled. Skipping."
    exit 0
}

$presetName = $project.enhancement.preset
$preset = $exports.enhancement_presets.$presetName
if ($null -eq $preset) {
    throw "Enhancement preset '$presetName' not found in export_presets.json"
}

$inVideo = Join-Path $root "04_OUTPUT\youtube_16x9\master_clean.mp4"
$outVideo = Join-Path $root "04_OUTPUT\youtube_16x9\master_enhanced.mp4"
if (-not (Test-Path $inVideo)) {
    throw "master_clean.mp4 missing for enhancement."
}

$chain = @()
if ($preset.scale_filter) {
    $chain += $preset.scale_filter
}
if ($preset.filters) {
    $chain += $preset.filters
}
if ($chain.Count -eq 0) {
    Write-Host "No enhancement filters defined; skipping."
    exit 0
}
$vf = ($chain -join ",")

& $ffmpeg -y -i $inVideo -vf $vf -c:v libx264 -preset medium -crf 17 -pix_fmt yuv420p -c:a copy $outVideo
if ($LASTEXITCODE -ne 0) { throw "Enhancement failed." }
Write-Host "Done: $outVideo"
