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
$subs = Join-Path $root "02_INPUT\lyrics\lyrics_styled.ass"
$out = Join-Path $root "04_OUTPUT\youtube_16x9\master_lyrics.mp4"
$subPath = (Resolve-Path $subs).Path -replace '\\','/'
$subPath = $subPath -replace ':','\:'
& $ffmpeg -y -i $video -vf "ass='$subPath'" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -c:a copy $out
if($LASTEXITCODE -ne 0){ throw "Burn failed." }
Write-Host "Done: $out"
