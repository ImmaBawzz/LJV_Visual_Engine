# Release Pipeline Runner with Checkpoint & Resume Support
# Usage:
#   powershell -ExecutionPolicy Bypass -File run_release_pipeline_resumable.ps1
#   powershell -ExecutionPolicy Bypass -File run_release_pipeline_resumable.ps1 -Resume
#   powershell -ExecutionPolicy Bypass -File run_release_pipeline_resumable.ps1 -Force

param(
    [switch]$Resume = $false,
    [switch]$Force = $false,
    [switch]$RequestStop = $false,
    [switch]$StopNow = $false
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$scriptsDir = Join-Path $root "05_SCRIPTS"
$checkpointScript = Join-Path $scriptsDir "core\checkpoint_manager.py"
$stopControlScript = Join-Path $scriptsDir "tools\stop_control.py"
$checkpointModuleDir = Join-Path $scriptsDir "core"
$checkpointModuleDirPy = ($checkpointModuleDir -replace "\\", "/")
$stopFile = Join-Path $root "stop.now"
$legacyStopFile = Join-Path $root "03_WORK\pipeline.stop"
$stopSigMaxAgeSec = 1800
if ($env:LJV_STOP_SIG_MAX_AGE_SEC) {
    $parsedMaxAge = 0
    if ([int]::TryParse($env:LJV_STOP_SIG_MAX_AGE_SEC, [ref]$parsedMaxAge) -and $parsedMaxAge -gt 0) {
        $stopSigMaxAgeSec = $parsedMaxAge
    }
}
$pipelineStart = Get-Date
$haltExitCode = 130

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

    $title = "LJV Release Pipeline"
    if ($env:LJV_NOTIFY_TITLE) {
        $title = $env:LJV_NOTIFY_TITLE
    }

    $ntfyServer = "https://ntfy.sh"
    if ($env:LJV_NOTIFY_NTFY_SERVER) {
        $ntfyServer = $env:LJV_NOTIFY_NTFY_SERVER.TrimEnd('/')
    }

    $config = @{
        Channel = $channel.ToLowerInvariant()
        Title = $title
        WebhookUrl = $env:LJV_NOTIFY_WEBHOOK_URL
        NtfyTopic = $env:LJV_NOTIFY_NTFY_TOPIC
        NtfyServer = $ntfyServer
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
    $emoji = "[INFO]"
    $priority = "default"
    $tag = "information_source"

    if ($statusLower -eq "success") {
        $emoji = "[SUCCESS]"
        $priority = "high"
        $tag = "white_check_mark"
    }
    elseif ($statusLower -eq "failed") {
        $emoji = "[FAILED]"
        $priority = "urgent"
        $tag = "x"
    }
    elseif ($statusLower -eq "running") {
        $emoji = "[START]"
        $priority = "high"
        $tag = "rocket"
    }
    elseif ($statusLower -eq "progress") {
        $emoji = "[PROGRESS]"
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
        $startMessage = "Pipeline execution started ({0} mode)." -f $mode
        Send-PipelineNotification -Config $notifierConfig -Status "running" -Message $startMessage
    }
}

# Show checkpoint status
function Show-Checkpoint-Status {
    Write-Host ""
    Write-Host "Pipeline Status:" -ForegroundColor Cyan
    python $checkpointScript --report
    Write-Host ""
}

function Get-HaltRequestFromCheckpoint {
    $checkpointPath = Join-Path $root "03_WORK\pipeline_checkpoint.json"
    if (-not (Test-Path $checkpointPath)) {
        return $null
    }

    try {
        $state = Get-Content $checkpointPath -Raw | ConvertFrom-Json
        if ($state.halt_request -and $state.halt_request.requested -eq $true) {
            return @{
                mode = if ($state.halt_request.mode) { $state.halt_request.mode } else { "graceful" }
                reason = if ($state.halt_request.reason) { $state.halt_request.reason } else { "Halt requested" }
                source = if ($state.halt_request.source) { $state.halt_request.source } else { "checkpoint" }
            }
        }
    }
    catch {
        Write-Host "Warning: unable to parse checkpoint halt state: $_" -ForegroundColor Yellow
    }

    return $null
}

function Get-HaltRequestFromSentinel {
    if (-not (Test-Path $stopFile)) {
        return $null
    }

    if (-not (Test-Path $stopControlScript)) {
        Write-Host "Signed stop file ignored: verifier script missing at $stopControlScript" -ForegroundColor Yellow
        return $null
    }

    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $verifyOutput = python $stopControlScript verify --input $stopFile --max-age-sec $stopSigMaxAgeSec --json 2>&1
    $verifyExitCode = $LASTEXITCODE
    $ErrorActionPreference = $prevEap

    if ($verifyExitCode -ne 0) {
        $details = ($verifyOutput | Out-String).Trim()
        if ($details) {
            Write-Host "Signed stop file ignored: $details" -ForegroundColor Yellow
        }
        else {
            Write-Host "Signed stop file ignored: verification failed." -ForegroundColor Yellow
        }
        return $null
    }

    $raw = ($verifyOutput | Out-String).Trim()
    if (-not $raw) {
        Write-Host "Signed stop file ignored: empty verifier output." -ForegroundColor Yellow
        return $null
    }

    try {
        $verify = $raw | ConvertFrom-Json
    }
    catch {
        Write-Host "Signed stop file ignored: invalid verifier JSON output." -ForegroundColor Yellow
        return $null
    }

    if (-not $verify.valid) {
        Write-Host "Signed stop file ignored: $($verify.message)" -ForegroundColor Yellow
        return $null
    }

    $resolvedMode = if ($verify.mode) { $verify.mode } else { "graceful" }
    $resolvedReason = if ($verify.reason) { $verify.reason } else { "Stop requested via signed stop.now" }

    return @{
        mode = $resolvedMode
        reason = $resolvedReason
        source = "signed_sentinel"
    }
}

function Get-HaltRequestFromLegacySentinel {
    if (-not (Test-Path $legacyStopFile)) {
        return $null
    }

    $mode = "graceful"
    try {
        $raw = (Get-Content $legacyStopFile -Raw).Trim().ToLowerInvariant()
        if ($raw -eq "immediate") {
            $mode = "immediate"
        }
    }
    catch {
        $mode = "graceful"
    }

    return @{
        mode = $mode
        reason = "Stop requested via legacy sentinel file"
        source = "legacy_sentinel"
    }
}

function Get-EffectiveHaltRequest {
    $checkpointRequest = Get-HaltRequestFromCheckpoint
    $sentinelRequest = Get-HaltRequestFromSentinel
    if (-not $sentinelRequest) {
        $sentinelRequest = Get-HaltRequestFromLegacySentinel
    }

    if ($checkpointRequest -and $sentinelRequest) {
        if ($checkpointRequest.mode -eq "immediate" -or $sentinelRequest.mode -eq "immediate") {
            return @{
                mode = "immediate"
                reason = "$($checkpointRequest.reason); $($sentinelRequest.reason)"
                source = "checkpoint+sentinel"
            }
        }

        return @{
            mode = "graceful"
            reason = "$($checkpointRequest.reason); $($sentinelRequest.reason)"
            source = "checkpoint+sentinel"
        }
    }

    if ($checkpointRequest) {
        return $checkpointRequest
    }

    return $sentinelRequest
}

function Set-HaltSentinel {
    param(
        [Parameter(Mandatory=$true)]
        [string]$mode
    )

    if (-not $env:LJV_STOP_SECRET) {
        Write-Host "Warning: LJV_STOP_SECRET is not set, signed stop.now file was not written." -ForegroundColor Yellow
        return $false
    }

    if (-not (Test-Path $stopControlScript)) {
        Write-Host "Warning: stop control script missing at $stopControlScript" -ForegroundColor Yellow
        return $false
    }

    $cmd = @($stopControlScript, "create", "--mode", $mode, "--reason", "Operator requested stop", "--output", $stopFile)

    if ($env:LJV_STOP_TOTP_SECRET) {
        $totpCode = $env:LJV_STOP_TOTP_CODE
        if (-not $totpCode) {
            $totpCode = Read-Host "Enter current 6-digit authenticator code for stop authorization"
        }
        if (-not $totpCode) {
            Write-Host "Warning: TOTP code missing, signed stop.now was not written." -ForegroundColor Yellow
            return $false
        }
        $cmd += @("--totp-code", $totpCode)
    }

    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $createOutput = python @cmd 2>&1
    $createExitCode = $LASTEXITCODE
    $ErrorActionPreference = $prevEap

    if ($createExitCode -ne 0) {
        $details = ($createOutput | Out-String).Trim()
        if ($details) {
            Write-Host "Warning: could not write signed stop.now: $details" -ForegroundColor Yellow
        }
        else {
            Write-Host "Warning: could not write signed stop.now." -ForegroundColor Yellow
        }
        return $false
    }

    return $true
}

function Clear-HaltSentinel {
    if (Test-Path $stopFile) {
        Remove-Item -Path $stopFile -Force
    }

    if (Test-Path $legacyStopFile) {
        Remove-Item -Path $legacyStopFile -Force
    }
}

function Register-RunContext {
    $runMode = "normal"
    if ($Resume) {
        $runMode = "resume"
    }
    elseif ($Force) {
        $runMode = "force"
    }

    $hostName = [System.Environment]::MachineName.Replace("'", "")
    Invoke-CheckpointCommand "cp.set_run_context($PID, '$hostName', '$runMode')"
}

function Handle-StopRequest {
    $requestedMode = "graceful"
    if ($StopNow) {
        $requestedMode = "immediate"
    }

    Write-Host "Requesting pipeline halt ($requestedMode)..." -ForegroundColor Yellow
    $wroteSignedSentinel = Set-HaltSentinel -mode $requestedMode

    Invoke-CheckpointCommand "cp.request_halt('$requestedMode', 'Operator requested stop', 'cli')"
    if ($requestedMode -eq "immediate") {
        Invoke-CheckpointCommand "cp.mark_running_steps_interrupted('Emergency stop requested by operator', $haltExitCode)"
        Invoke-CheckpointCommand "cp.mark_pipeline_halted('immediate', 'Emergency stop requested by operator', None)"

        $checkpointPath = Join-Path $root "03_WORK\pipeline_checkpoint.json"
        $runnerPid = $null
        if (Test-Path $checkpointPath) {
            try {
                $state = Get-Content $checkpointPath -Raw | ConvertFrom-Json
                if ($state.run_context -and $state.run_context.active -eq $true -and $state.run_context.pid) {
                    $runnerPid = [int]$state.run_context.pid
                }
            }
            catch {
                Write-Host "Warning: could not read active runner PID from checkpoint." -ForegroundColor Yellow
            }
        }

        if ($runnerPid -and $runnerPid -ne $PID) {
            Write-Host "Terminating active pipeline process tree (PID $runnerPid)..." -ForegroundColor Yellow
            & taskkill /PID $runnerPid /T /F | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Emergency stop signal delivered." -ForegroundColor Green
            }
            else {
                Write-Host "Warning: could not terminate PID $runnerPid (it may have already exited)." -ForegroundColor Yellow
            }
        }
        else {
            Write-Host "No active pipeline process detected. Halt request recorded." -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "Graceful halt requested. Active step will finish before stopping." -ForegroundColor Green
    }

    if ($wroteSignedSentinel) {
        Write-Host "Signed stop sentinel written to stop.now" -ForegroundColor Gray
    }
}

function Invoke-CheckpointCommand {
    param(
        [Parameter(Mandatory=$true)]
        [string]$commandBody
    )

    $pythonCmd = "import sys; sys.path.insert(0, '" + $checkpointModuleDirPy + "'); from checkpoint_manager import get_checkpoint; cp = get_checkpoint(); " + $commandBody
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $commandOutput = python -c $pythonCmd 2>&1
    $pythonExitCode = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($pythonExitCode -ne 0) {
        $details = ""
        if ($commandOutput) {
            $details = ($commandOutput | Out-String)
        }
        throw "Checkpoint command failed.`nBody: $commandBody`nPython: $pythonCmd`nOutput:`n$details"
    }
}

function Get-ResumeStepFromCheckpoint {
    $checkpointPath = Join-Path $root "03_WORK\pipeline_checkpoint.json"
    if (-not (Test-Path $checkpointPath)) {
        return 1
    }

    try {
        $state = Get-Content $checkpointPath -Raw | ConvertFrom-Json
        if (-not $state.steps) {
            return 1
        }

        $pending = @()
        foreach ($prop in $state.steps.PSObject.Properties) {
            $id = [int]$prop.Name
            $status = $prop.Value.status
            if ($status -ne "completed") {
                $pending += $id
            }
        }

        if ($pending.Count -gt 0) {
            return ($pending | Measure-Object -Minimum).Minimum
        }

        return 1
    }
    catch {
        return 1
    }
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
        $validationCmd = "import sys; sys.path.insert(0, '" + $checkpointModuleDirPy + "'); from checkpoint_manager import get_checkpoint; cp = get_checkpoint(); cp.validate_step_output(" + $stepId + ")"
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $validationOutput = python -c $validationCmd 2>&1
        $validationExitCode = $LASTEXITCODE
        $ErrorActionPreference = $prevEap

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
            Write-Host "[FAIL] Step $stepId failed output validation" -ForegroundColor Red
            return $validationExitCode
        }

        Invoke-CheckpointCommand "cp.mark_step_complete($stepId, '$stepName', 0)"
        Write-Host "[OK] Step $stepId complete" -ForegroundColor Green
        if ($notifierConfig) {
            Send-PipelineNotification -Config $notifierConfig -Status "progress" -StepId $stepId -StepName $stepName -StepTotal $totalSteps -Message "Step completed successfully."
        }
    }
    else {
        $errorMsg = "Exit code $exitCode"
        Invoke-CheckpointCommand "cp.mark_step_failed($stepId, '$stepName', $exitCode, '$errorMsg')"
        Write-Host "[FAIL] Step $stepId failed (exit code: $exitCode)" -ForegroundColor Red
        if ($notifierConfig) {
            Send-PipelineNotification -Config $notifierConfig -Status "failed" -StepId $stepId -StepName $stepName -StepTotal $totalSteps -Message "Step failed with exit code $exitCode."
        }
    }

    return $exitCode
}

# Main execution
try {
    if ($RequestStop) {
        Handle-StopRequest
        exit 0
    }

    Initialize-Checkpoint
    Register-RunContext

    $existingHalt = Get-EffectiveHaltRequest
    if ($existingHalt) {
        Write-Host "A halt request is currently active ($($existingHalt.mode))." -ForegroundColor Yellow
        Write-Host "Clear the request before starting a new run with: python core\checkpoint_manager.py --clear-halt" -ForegroundColor Yellow
        exit $haltExitCode
    }

    Clear-HaltSentinel
    Invoke-CheckpointCommand "cp.clear_halt_request()"

    Show-Checkpoint-Status

    # Determine starting point
    $startStep = 1
    if ($Resume) {
        $startStep = Get-ResumeStepFromCheckpoint
        Write-Host "Resuming from step $startStep" -ForegroundColor Yellow
    }

    # Execute steps
    $failedStep = $null
    foreach ($step in $steps) {
        if ($step.ID -lt $startStep) {
            Write-Host "[$($step.ID)/$totalSteps] SKIPPED: $($step.Name)" -ForegroundColor DarkGray
            continue
        }

        $haltRequest = Get-EffectiveHaltRequest
        if ($haltRequest) {
            $haltReason = "$($haltRequest.reason) (source: $($haltRequest.source))"
            $haltAtStep = $step.ID
            Invoke-CheckpointCommand "cp.mark_pipeline_halted('$($haltRequest.mode)', '$haltReason', $haltAtStep)"
            Write-Host "Pipeline halted before step $haltAtStep due to $($haltRequest.mode) stop request." -ForegroundColor Yellow
            $failedStep = $null
            break
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

    $finalHaltRequest = Get-HaltRequestFromCheckpoint
    if ($finalHaltRequest -or (Test-Path $stopFile) -or (Test-Path $legacyStopFile)) {
        Write-Host "Pipeline halted by operator request. Resume when ready using -Resume." -ForegroundColor Yellow
        if ($notifierConfig) {
            Send-PipelineNotification -Config $notifierConfig -Status "failed" -StepTotal $totalSteps -Message "Pipeline halted by operator request."
        }
        Invoke-CheckpointCommand "cp.clear_run_context()"
        exit $haltExitCode
    }
    elseif ($failedStep) {
        Write-Host "Pipeline failed at step $failedStep. To resume, run:" -ForegroundColor Yellow
        Write-Host "  powershell -ExecutionPolicy Bypass -File run_release_pipeline_resumable.ps1 -Resume" -ForegroundColor Cyan
        if ($notifierConfig) {
            Send-PipelineNotification -Config $notifierConfig -Status "failed" -StepId $failedStep -StepTotal $totalSteps -Message "Pipeline failed. Run with -Resume after fixing the issue."
        }
        Invoke-CheckpointCommand "cp.clear_run_context()"
        exit 1
    }
    else {
        Write-Host "Pipeline complete!" -ForegroundColor Green
        if ($notifierConfig) {
            Send-PipelineNotification -Config $notifierConfig -Status "success" -StepTotal $totalSteps -Message "Pipeline completed successfully. Outputs and reports are ready for review."
        }
        Invoke-CheckpointCommand "cp.clear_run_context()"
        exit 0
    }
}
catch {
    Write-Host "Fatal error: $_" -ForegroundColor Red
    if ($notifierConfig) {
        Send-PipelineNotification -Config $notifierConfig -Status "failed" -StepTotal $totalSteps -Message "Fatal pipeline error: $_"
    }
    try {
        Invoke-CheckpointCommand "cp.clear_run_context()"
    }
    catch {
        Write-Host "Warning: could not clear run context after fatal error." -ForegroundColor Yellow
    }
    exit 1
}
