param(
    [int]$Port = 8787,
    [string]$BindHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$dashboardDir = $PSScriptRoot
$repoRoot = Split-Path -Parent (Split-Path -Parent $dashboardDir)

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonCmd = $venvPython
} else {
    $pythonCmd = "python"
}

Write-Host "Starting LJV dashboard on http://$BindHost`:$Port" -ForegroundColor Cyan
Push-Location $dashboardDir
try {
    & $pythonCmd ".\app.py" --host $BindHost --port $Port
}
finally {
    Pop-Location
}
