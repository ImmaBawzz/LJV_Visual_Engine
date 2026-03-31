# Release Pipeline Runner with Checkpoint & Resume Support
# Usage:
#   powershell -ExecutionPolicy Bypass -File run_release_pipeline_resumable.ps1
#   powershell -ExecutionPolicy Bypass -File run_release_pipeline_resumable.ps1 -Resume
#   powershell -ExecutionPolicy Bypass -File run_release_pipeline_resumable.ps1 -Force

param(
    [switch]$Resume = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$scriptsDir = Join-Path $root "05_SCRIPTS"
$checkpointScript = Join-Path $scriptsDir "core\checkpoint_manager.py"
$checkpointModuleDir = Join-Path $scriptsDir "core"

# Define pipeline steps
$steps = @(
    @{ ID=1; Name="Validate Environment"; Type="ps1"; Script="core\01_validate_environment.ps1" },
    @{ ID=2; Name="Preflight Input Validation"; Type="py"; Script="core\01b_preflight_validate.py" },
    @{ ID=3; Name="Prepare Inputs"; Type="py"; Script="core\02_prepare_inputs.py" },
    @{ ID=4; Name="Build Pingpong Loop"; Type="bat"; Script="core\03_build_pingpong_loop.bat" },
    @{ ID=5; Name="Build Loop Variants"; Type="py"; Script="core\04_build_loop_variants.py" },
    @{ ID=6; Name="Align Lyrics To Audio"; Type="ps1"; Script="core\05b_align_lyrics_to_audio.ps1" },
    @{ ID=7; Name="Generate ASS Subtitles"; Type="py"; Script="core\05_generate_ass_from_txt.py"; Args=@("--preset", "spotify_clean") },
    @{ ID=8; Name="Build Title Cards"; Type="py"; Script="core\08_build_title_cards.py" },
    @{ ID=9; Name="Build Sections"; Type="py"; Script="core\09_build_sections.py" },
    @{ ID=10; Name="Audio Reactive Pass"; Type="py"; Script="analysis\13_audio_reactive_pass.py" },
    @{ ID=11; Name="Build Simple Beatmap"; Type="py"; Script="analysis\14_build_simple_beatmap.py" },
    @{ ID=12; Name="Build Timeline Manifest"; Type="py"; Script="analysis\15_build_timeline_manifest.py" },
    @{ ID=13; Name="Render Master Video"; Type="ps1"; Script="render\10_render_master_video.ps1" },
    @{ ID=14; Name="Render Social Exports"; Type="ps1"; Script="social\12_render_social_exports.ps1" },
    @{ ID=15; Name="Render Teasers"; Type="py"; Script="social\13_render_teasers.py" },
    @{ ID=16; Name="Quality Gate Auto Check"; Type="py"; Script="release\16_run_quality_gate.py" },
    @{ ID=17; Name="Write Delivery Manifest"; Type="py"; Script="tools\16_write_delivery_manifest.py" },
    @{ ID=18; Name="Write Release Report"; Type="py"; Script="release\17_write_release_report.py" },
    @{ ID=19; Name="Build Release Bundle"; Type="py"; Script="release\18_build_release_bundle.py" }
)

$totalSteps = $steps.Count

# Initialize checkpoint
function Initialize-Checkpoint {
    Write-Host "Initializing pipeline checkpoint..." -ForegroundColor Cyan
    
    if ($Force) {
        Write-Host "Force flag detected: resetting checkpoint..." -ForegroundColor Yellow
        python $checkpointScript --reset
    }
    elseif ($Resume) {
        Write-Host "Resume flag detected: will resume from last failure" -ForegroundColor Yellow
    }
}

# Show checkpoint status
function Show-Checkpoint-Status {
    Write-Host ""
    Write-Host "Pipeline Status:" -ForegroundColor Cyan
    python $checkpointScript --report
    Write-Host ""
}

function Invoke-CheckpointCommand {
    param(
        [Parameter(Mandatory=$true)]
        [string]$commandBody
    )

    $pythonCmd = "import sys; sys.path.insert(0, '" + $checkpointModuleDir + "'); from checkpoint_manager import get_checkpoint; cp = get_checkpoint(); " + $commandBody
    python -c $pythonCmd 2>$null
}

# Execute a single step
function Execute-Step {
    param(
        [object]$step,
        [string]$checkpointMgr
    )

    $stepId = $step.ID
    $stepName = $step.Name
    $scriptPath = Join-Path $scriptsDir $step.Script
    $scriptType = $step.Type
    $scriptArgs = $step.Args

    if (-not (Test-Path $scriptPath)) {
        Write-Host "ERROR: Script not found: $scriptPath" -ForegroundColor Red
        Invoke-CheckpointCommand "cp.mark_step_failed($stepId, '$stepName', 127, 'Script not found')"
        return 127
    }

    Write-Host ""
    Write-Host "[$stepId/$totalSteps] Executing: $stepName" -ForegroundColor Green
    Write-Host "Script: $scriptPath" -ForegroundColor Gray

    # Start checkpoint
    Invoke-CheckpointCommand "cp.mark_step_started($stepId, '$stepName')"

    # Execute script
    $exitCode = 0
    try {
        if ($scriptType -eq "ps1") {
            & powershell -ExecutionPolicy Bypass -File $scriptPath
            $exitCode = $LASTEXITCODE
        }
        elseif ($scriptType -eq "py") {
            if ($scriptArgs -and $scriptArgs.Count -gt 0) {
                python $scriptPath @scriptArgs
            } else {
                python $scriptPath
            }
            $exitCode = $LASTEXITCODE
        }
        elseif ($scriptType -eq "bat") {
            & cmd /c "$scriptPath"
            $exitCode = $LASTEXITCODE
        }
    }
    catch {
        Write-Host "Exception during execution: $_" -ForegroundColor Red
        $exitCode = 1
    }

    # Record result
    if ($exitCode -eq 0) {
        Invoke-CheckpointCommand "cp.mark_step_complete($stepId, '$stepName', 0)"
        Write-Host "✓ Step $stepId complete" -ForegroundColor Green
    }
    else {
        $errorMsg = "Exit code $exitCode"
        Invoke-CheckpointCommand "cp.mark_step_failed($stepId, '$stepName', $exitCode, '$errorMsg')"
        Write-Host "✗ Step $stepId failed (exit code: $exitCode)" -ForegroundColor Red
    }

    return $exitCode
}

# Main execution
try {
    Initialize-Checkpoint
    Show-Checkpoint-Status

    # Determine starting point
    $startStep = 1
    if ($Resume) {
        $resumeCmd = "import sys; sys.path.insert(0, '" + $checkpointModuleDir + "'); from checkpoint_manager import get_checkpoint; cp = get_checkpoint(); rp = cp.get_resume_point(); print(rp if rp else 1)"
        $resumePoint = python -c $resumeCmd 2>$null | Select-Object -Last 1
        if ($resumePoint -and $resumePoint -ne "None") {
            $startStep = [int]$resumePoint
            Write-Host "Resuming from step $startStep" -ForegroundColor Yellow
        }
    }

    # Execute steps
    $failedStep = $null
    foreach ($step in $steps) {
        if ($step.ID -lt $startStep) {
            Write-Host "[$($step.ID)/$totalSteps] SKIPPED: $($step.Name)" -ForegroundColor DarkGray
            continue
        }

        $exitCode = Execute-Step $step $checkpointScript
        if ($exitCode -ne 0) {
            $failedStep = $step.ID
            break
        }
    }

    # Final status
    Write-Host ""
    Show-Checkpoint-Status

    if ($failedStep) {
        Write-Host "Pipeline failed at step $failedStep. To resume, run:" -ForegroundColor Yellow
        Write-Host "  powershell -ExecutionPolicy Bypass -File run_release_pipeline_resumable.ps1 -Resume" -ForegroundColor Cyan
        exit 1
    }
    else {
        Write-Host "Pipeline complete!" -ForegroundColor Green
        exit 0
    }
}
catch {
    Write-Host "Fatal error: $_" -ForegroundColor Red
    exit 1
}
