# Configure GitHub Repository Topics
# Updates repository topics to improve discoverability

param(
    [string]$GitHubToken = ""
)

# If token not provided, try environment variable
if (-not $GitHubToken) {
    $GitHubToken = $env:GITHUB_TOKEN
}

if (-not $GitHubToken) {
    Write-Host "❌ GitHub token not provided" -ForegroundColor Red
    Write-Host "Set GITHUB_TOKEN environment variable or pass -GitHubToken parameter" -ForegroundColor Yellow
    exit 1
}

# Configuration
$owner = "ImmaBawzz"
$repo = "LJV_Visual_Engine"

# Topics to add
$topics = @(
    "music-visualization",
    "lyric-video",
    "audio-reactive",
    "ffmpeg",
    "python",
    "video-pipeline",
    "music-production",
    "whisper-asr",
    "checkpoint-recovery",
    "batch-processing",
    "quality-assurance",
    "music-tech",
    "audio-synchronization",
    "subtitle-automation",
    "video-production"
)

Write-Host "Configuring GitHub repository topics for $owner/$repo" -ForegroundColor Cyan
Write-Host ""

# Set environment variable for Python script
$env:GITHUB_TOKEN = $GitHubToken

# Run Python script
$scriptPath = "05_SCRIPTS\tools\configure_github_topics.py"

if (Test-Path $scriptPath) {
    Write-Host "Running topic configuration script..." -ForegroundColor Green
    python $scriptPath
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Topics configured successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Verify at: https://github.com/$owner/$repo" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "❌ Topic configuration failed" -ForegroundColor Red
        Write-Host "Check token permissions and try again" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Script not found: $scriptPath" -ForegroundColor Red
    exit 1
}