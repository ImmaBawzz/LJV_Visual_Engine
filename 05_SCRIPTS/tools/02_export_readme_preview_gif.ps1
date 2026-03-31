param(
    [Parameter(Mandatory = $true)]
    [string]$SourceVideo,
    [string]$OutputGif = ".github/assets/readme-preview.gif",
    [double]$StartSec = 0,
    [double]$DurationSec = 8,
    [int]$Width = 960,
    [int]$Fps = 12
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pathsConfigPath = Join-Path $root "01_CONFIG\paths_config.json"
$resolvedSource = if ([System.IO.Path]::IsPathRooted($SourceVideo)) { $SourceVideo } else { Join-Path $root $SourceVideo }
$resolvedOutput = if ([System.IO.Path]::IsPathRooted($OutputGif)) { $OutputGif } else { Join-Path $root $OutputGif }

if (-not (Test-Path $resolvedSource)) {
    throw "Source video not found: $resolvedSource"
}

$ffmpeg = "ffmpeg"
if (Test-Path $pathsConfigPath) {
    $config = Get-Content $pathsConfigPath -Raw | ConvertFrom-Json
    if ($config.ffmpeg) {
        $ffmpeg = $config.ffmpeg
    }
}

if (-not (Get-Command $ffmpeg -ErrorAction SilentlyContinue) -and -not (Test-Path $ffmpeg)) {
    throw "ffmpeg is not resolvable. Add it to PATH or set 01_CONFIG/paths_config.json."
}

$outputDir = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$palettePath = Join-Path ([System.IO.Path]::GetTempPath()) ("readme-preview-" + [guid]::NewGuid().ToString() + ".png")
$filter = "fps=$Fps,scale=${Width}:-1:flags=lanczos"

try {
    & $ffmpeg -y -ss $StartSec -t $DurationSec -i $resolvedSource -vf "$filter,palettegen=stats_mode=diff" $palettePath | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "ffmpeg palette generation failed"
    }

    & $ffmpeg -y -ss $StartSec -t $DurationSec -i $resolvedSource -i $palettePath -lavfi "$filter[x];[x][1:v]paletteuse=dither=sierra2_4a" $resolvedOutput | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "ffmpeg gif export failed"
    }
}
finally {
    if (Test-Path $palettePath) {
        Remove-Item $palettePath -Force
    }
}

Write-Host "GIF written to $resolvedOutput"
Write-Host "Review the clip, then commit it only if it is safe for public release."