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
$pipelineStart = Get-Date

# Optional notification settings (environment variables)
#   LJV_NOTIFY_CHANNEL=ntfy|discord|slack|webhook
#   LJV_NOTIFY_TITLE="LJV Pipeline"
# For ntfy:
#   LJV_NOTIFY_NTFY_TOPIC=your-topic
#   LJV_NOTIFY_NTFY_SERVER=https://ntfy.sh
# For discord/slack/webhook:
#   LJV_NOTIFY_WEBHOOK_URL=https://...
function Get-NotifierConfig {
    $channel = $env:LJV_NOTIFY_CHANNEL
    if (-not $channel) {
        return $null
    }

    $config = @{
        Channel = $channel.ToLowerInvariant()
        Title = if ($env:LJV_NOTIFY_TITLE) { $env:LJV_NOTIFY_TITLE } else { "LJV Release Pipeline" }
        WebhookUrl = $env:LJV_NOTIFY_WEBHOOK_URL
        NtfyTopic = $env:LJV_NOTIFY_NTFY_TOPIC
        NtfyServer = if ($env:LJV_NOTIFY_NTFY_SERVER) { $env:LJV_NOTIFY_NTFY_SERVER.TrimEnd('/') } else { "https://ntfy.sh" }
    }

    return $config
}

function Send-PipelineNotification {
    param(
        [Parameter(Mandatory=$true)]
        [hashtable]$Config,

        [Parameter(Mandatory=$true)]
        [string]$Status,

        [string]$Message,
        [int]$StepId = 0,
        [string]$StepName = "",
        [int]$StepTotal = 0
    )

    $elapsed = [math]::Round(((Get-Date) - $pipelineStart).TotalMinutes, 1)
    $statusLower = $Status.ToLowerInvariant()
    $emoji = "ℹ"
    $priority = "default"
    $tag = "information_source"

    if ($statusLower -eq "success") {
        $emoji = "✅"
        $priority = "high"
        $tag = "white_check_mark"
    }
    elseif ($statusLower -eq "failed") {
        $emoji = "❌"
        $priority = "urgent"
        $tag = "x"
    }
    elseif ($statusLower -eq "running") {
        $emoji = "🚀"
        $priority = "high"
        $tag = "rocket"
    }
    elseif ($statusLower -eq "progress") {
        $emoji = "🔄"
        $priority = "default"
        $tag = "arrows_counterclockwise"
    }

    $stepSummary = ""
    if ($StepId -gt 0 -and $StepTotal -gt 0) {
        $stepSummary = "Step $StepId/$StepTotal"
        if ($StepName) {
            $stepSummary = "$stepSummary - $StepName"
        }
    }

    $lines = @("$emoji [$($Config.Title)] $Status")
    if ($stepSummary) {
        $lines += $stepSummary
    }
    if ($Message) {
        $lines += $Message
    }
    $lines += "Elapsed: $elapsed min"
    $textBody = ($lines -join "`n")

    try {
        switch ($Config.Channel) {
            "ntfy" {
                if (-not $Config.NtfyTopic) {
                    Write-Host "Notification skipped: LJV_NOTIFY_NTFY_TOPIC is not set." -ForegroundColor Yellow
                    return
                }
                $url = "$($Config.NtfyServer)/$($Config.NtfyTopic)"
                $headers = @{
                    "Title" = $Config.Title
                    "Priority" = $priority
                    "Tags" = $tag
                }
                Invoke-RestMethod -Method Post -Uri $url -Headers $headers -Body $textBody | Out-Null
            }
            "discord" {
                if (-not $Config.WebhookUrl) {
                    Write-Host "Notification skipped: LJV_NOTIFY_WEBHOOK_URL is not set." -ForegroundColor Yellow
                    return
                }
                $payload = @{ content = $textBody } | ConvertTo-Json -Compress
                Invoke-RestMethod -Method Post -Uri $Config.WebhookUrl -ContentType "application/json" -Body $payload | Out-Null
            }
            "slack" {
                if (-not $Config.WebhookUrl) {
                    Write-Host "Notification skipped: LJV_NOTIFY_WEBHOOK_URL is not set." -ForegroundColor Yellow
                    return
                }
                $payload = @{ text = $textBody } | ConvertTo-Json -Compress
                Invoke-RestMethod -Method Post -Uri $Config.WebhookUrl -ContentType "application/json" -Body $payload | Out-Null
            }
            "webhook" {
                if (-not $Config.WebhookUrl) {
                    Write-Host "Notification skipped: LJV_NOTIFY_WEBHOOK_URL is not set." -ForegroundColor Yellow
                    return
                }
                $payload = @{
                    title = $Config.Title
                    status = $Status
                    stepId = $StepId
                    stepName = $StepName
                    totalSteps = $StepTotal
                    elapsedMinutes = $elapsed
                    message = $Message
                    timestamp = (Get-Date).ToString("o")
                } | ConvertTo-Json
                Invoke-RestMethod -Method Post -Uri $Config.WebhookUrl -ContentType "application/json" -Body $payload | Out-Null
            }
            default {
                Write-Host "Notification skipped: unsupported channel '$($Config.Channel)'" -ForegroundColor Yellow
            }
        }
    }
    catch {
        Write-Host "Notification send failed: $_" -ForegroundColor Yellow
    }
}

$notifierConfig = Get-NotifierConfig

# Define pipeline steps
$steps = @(
    @{ ID=1; Name="Validate Environment"; Type="ps1"; Script="core\01_validate_environment.ps1" },
    @{ ID=2; Name="Preflight Input Validation"; Type="py"; Script="core\01b_preflight_validate.py" },
    @{ ID=3; Name="Schema Validation"; Type="py"; Script="core\01c_validate_schemas.py" },
    @{ ID=4; Name="Prepare Inputs"; Type="py"; Script="core\02_prepare_inputs.py" },
    @{ ID=5; Name="Build Pingpong Loop"; Type="bat"; Script="core\03_build_pingpong_loop.bat" },
    @{ ID=6; Name="Build Loop Variants"; Type="py"; Script="core\04_build_loop_variants.py" },
    @{ ID=7; Name="Align Lyrics To Audio"; Type="ps1"; Script="core\05b_align_lyrics_to_audio.ps1" },
    @{ ID=8; Name="Generate ASS Subtitles"; Type="py"; Script="core\05_generate_ass_from_txt.py"; Args=@("--preset", "spotify_clean") },
    @{ ID=9; Name="Build Title Cards"; Type="py"; Script="core\08_build_title_cards.py" },
    @{ ID=10; Name="Build Sections"; Type="py"; Script="core\09_build_sections.py" },
    @{ ID=11; Name="Audio Reactive Pass"; Type="py"; Script="analysis\13_audio_reactive_pass.py" },
    @{ ID=12; Name="Build Simple Beatmap"; Type="py"; Script="analysis\14_build_simple_beatmap.py" },
    @{ ID=13; Name="Build Timeline Manifest"; Type="py"; Script="analysis\15_build_timeline_manifest.py" },
    @{ ID=14; Name="Render Master Video"; Type="ps1"; Script="render\10_render_master_video.ps1" },
    @{ ID=15; Name="Render Social Exports"; Type="ps1"; Script="social\12_render_social_exports.ps1" },
    @{ ID=16; Name="Render Teasers"; Type="py"; Script="social\13_render_teasers.py" },
    @{ ID=17; Name="Quality Gate Auto Check"; Type="py"; Script="release\16_run_quality_gate.py" },
    @{ ID=18; Name="Write Delivery Manifest"; Type="py"; Script="tools\16_write_delivery_manifest.py" },
    @{ ID=19; Name="Write Release Report"; Type="py"; Script="release\17_write_release_report.py" },
    @{ ID=20; Name="Build Release Bundle"; Type="py"; Script="release\18_build_release_bundle.py" }
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

    if ($notifierConfig) {
        $mode = "normal"
        if ($Resume) { $mode = "resume" }
        elseif ($Force) { $mode = "force" }
        Send-PipelineNotification -Config $notifierConfig -Status "running" -Message "Pipeline execution started ($mode mode)."
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

    if ($notifierConfig) {
        Send-PipelineNotification -Config $notifierConfig -Status "progress" -StepId $stepId -StepName $stepName -StepTotal $totalSteps -Message "Step started."
    }

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
        $validationCmd = "import sys; sys.path.insert(0, '" + $checkpointModuleDir + "'); from checkpoint_manager import get_checkpoint; cp = get_checkpoint(); " + `
            "try: cp.validate_step_output(" + $stepId + ")" + `
            "`nexcept Exception as ex: print('VALIDATION_ERROR: ' + str(ex)); raise SystemExit(2)"
        $validationOutput = python -c $validationCmd 2>&1
        $validationExitCode = $LASTEXITCODE

        if ($validationExitCode -ne 0) {
            $validationError = "Output validation failed for step $stepId"
            if ($validationOutput) {
                $trimmed = ($validationOutput | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
                if ($trimmed.Count -gt 0) {
                    $firstLine = $trimmed[0]
                    $validationError = $firstLine
                    Write-Host "Validation details:" -ForegroundColor Yellow
                    foreach ($line in $trimmed) {
                        Write-Host "  $line" -ForegroundColor Yellow
                    }
                }
            }
            $safeValidationError = $validationError.Replace("'", "\\'")
            Invoke-CheckpointCommand "cp.mark_step_failed($stepId, '$stepName', $validationExitCode, '$safeValidationError')"
            Write-Host "✗ Step $stepId failed output validation" -ForegroundColor Red
            return $validationExitCode
        }

        Invoke-CheckpointCommand "cp.mark_step_complete($stepId, '$stepName', 0)"
        Write-Host "✓ Step $stepId complete" -ForegroundColor Green
        if ($notifierConfig) {
            Send-PipelineNotification -Config $notifierConfig -Status "progress" -StepId $stepId -StepName $stepName -StepTotal $totalSteps -Message "Step completed successfully."
        }
    }
    else {
        $errorMsg = "Exit code $exitCode"
        Invoke-CheckpointCommand "cp.mark_step_failed($stepId, '$stepName', $exitCode, '$errorMsg')"
        Write-Host "✗ Step $stepId failed (exit code: $exitCode)" -ForegroundColor Red
        if ($notifierConfig) {
            Send-PipelineNotification -Config $notifierConfig -Status "failed" -StepId $stepId -StepName $stepName -StepTotal $totalSteps -Message "Step failed with exit code $exitCode."
        }
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
        if ($notifierConfig) {
            Send-PipelineNotification -Config $notifierConfig -Status "failed" -StepId $failedStep -StepTotal $totalSteps -Message "Pipeline failed. Run with -Resume after fixing the issue."
        }
        exit 1
    }
    else {
        Write-Host "Pipeline complete!" -ForegroundColor Green
        if ($notifierConfig) {
            Send-PipelineNotification -Config $notifierConfig -Status "success" -StepTotal $totalSteps -Message "Pipeline completed successfully. Outputs and reports are ready for review."
        }
        exit 0
    }
}
catch {
    Write-Host "Fatal error: $_" -ForegroundColor Red
    if ($notifierConfig) {
        Send-PipelineNotification -Config $notifierConfig -Status "failed" -StepTotal $totalSteps -Message "Fatal pipeline error: $_"
    }
    exit 1
}
