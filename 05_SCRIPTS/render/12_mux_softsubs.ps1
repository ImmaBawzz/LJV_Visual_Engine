$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$paths = Get-Content (Join-Path $root "01_CONFIG\paths_config.json") -Raw | ConvertFrom-Json
$project = Get-Content (Join-Path $root "01_CONFIG\project_config.json") -Raw | ConvertFrom-Json
$ffmpeg = $paths.ffmpeg
$video = Join-Path $root "04_OUTPUT\youtube_16x9\master_clean.mp4"
$enhancedVideo = Join-Path $root "04_OUTPUT\youtube_16x9\master_enhanced.mp4"
if($project.enhancement.enabled -eq $true -and (Test-Path $enhancedVideo)){
	$video = $enhancedVideo
}
$subs = Join-Path $root "02_INPUT\lyrics\lyrics_timed.srt"
$out = Join-Path $root "04_OUTPUT\youtube_16x9\master_softsubs.mp4"
& $ffmpeg -y -i $video -i $subs -c:v copy -c:a copy -c:s mov_text $out
if($LASTEXITCODE -ne 0){ throw "Softsub mux failed." }
Write-Host "Done: $out"
