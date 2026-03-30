$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$config = Get-Content (Join-Path $root "01_CONFIG\paths_config.json") -Raw | ConvertFrom-Json
$project = Get-Content (Join-Path $root "01_CONFIG\project_config.json") -Raw | ConvertFrom-Json
$log = Join-Path $root "03_WORK\logs\01_validate_environment.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log -Parent) | Out-Null
function W($m){$m | Tee-Object -FilePath $log -Append}

foreach($name in @("ffmpeg","ffprobe","font_primary")){
  $path = $config.$name
  if(Test-Path $path){ W "OK $name -> $path" } else { W "FAIL $name -> $path"; throw "$name missing" }
}

if(-not $project.song_duration_sec -or $project.song_duration_sec -le 0){
  W "FAIL project_config.song_duration_sec must be > 0"
  throw "Invalid song duration"
}

if(-not $project.artist -or -not $project.title){
  W "FAIL project_config artist/title missing"
  throw "Missing project metadata"
}

$ffmpegVersion = & $config.ffmpeg -version 2>$null | Select-Object -First 1
if($LASTEXITCODE -eq 0){
  W "OK ffmpeg executable responds: $ffmpegVersion"
} else {
  W "FAIL ffmpeg executable failed to run"
  throw "ffmpeg not executable"
}

$ffprobeVersion = & $config.ffprobe -version 2>$null | Select-Object -First 1
if($LASTEXITCODE -eq 0){
  W "OK ffprobe executable responds: $ffprobeVersion"
} else {
  W "FAIL ffprobe executable failed to run"
  throw "ffprobe not executable"
}

W "Validation complete."
