$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$config = Get-Content (Join-Path $root "01_CONFIG\paths_config.json") -Raw | ConvertFrom-Json
$project = Get-Content (Join-Path $root "01_CONFIG\project_config.json") -Raw | ConvertFrom-Json
$log = Join-Path $root "03_WORK\logs\01_validate_environment.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log -Parent) | Out-Null
function W($m){$m | Tee-Object -FilePath $log -Append}

function Resolve-ConfiguredTool($value){
  if(-not $value){ return $null }
  if(Test-Path $value){ return (Resolve-Path $value).Path }
  $command = Get-Command $value -ErrorAction SilentlyContinue
  if($command){ return $command.Source }
  return $null
}

$ffmpegPath = Resolve-ConfiguredTool $config.ffmpeg
if($ffmpegPath){ W "OK ffmpeg -> $ffmpegPath" } else { W "FAIL ffmpeg -> $($config.ffmpeg)"; throw "ffmpeg missing" }

$ffprobePath = Resolve-ConfiguredTool $config.ffprobe
if($ffprobePath){ W "OK ffprobe -> $ffprobePath" } else { W "FAIL ffprobe -> $($config.ffprobe)"; throw "ffprobe missing" }

if($config.font_primary){ W "OK font_primary configured: $($config.font_primary)" } else { W "FAIL font_primary is empty"; throw "font_primary missing" }

if(-not $project.song_duration_sec -or $project.song_duration_sec -le 0){
  W "FAIL project_config.song_duration_sec must be > 0"
  throw "Invalid song duration"
}

if(-not $project.artist -or -not $project.title){
  W "FAIL project_config artist/title missing"
  throw "Missing project metadata"
}

$ffmpegVersion = & $ffmpegPath -version 2>$null | Select-Object -First 1
if($LASTEXITCODE -eq 0){
  W "OK ffmpeg executable responds: $ffmpegVersion"
} else {
  W "FAIL ffmpeg executable failed to run"
  throw "ffmpeg not executable"
}

$ffprobeVersion = & $ffprobePath -version 2>$null | Select-Object -First 1
if($LASTEXITCODE -eq 0){
  W "OK ffprobe executable responds: $ffprobeVersion"
} else {
  W "FAIL ffprobe executable failed to run"
  throw "ffprobe not executable"
}

W "Validation complete."
