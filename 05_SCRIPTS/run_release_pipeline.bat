@echo off
REM Release Pipeline Runner with Checkpoint & Resume Support
REM Double-click to run, or use:
REM   run_release_pipeline.bat              - Run from start
REM   run_release_pipeline.bat resume       - Resume from last failure
REM   run_release_pipeline.bat force        - Force restart (clear checkpoint)
REM   run_release_pipeline.bat status       - Check pipeline status
REM   run_release_pipeline.bat log          - View execution log

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if "%1"=="" (
    REM Default: run pipeline
    powershell -ExecutionPolicy Bypass -File "run_release_pipeline_resumable.ps1"
    exit /b !errorlevel!
)

set "CMD=%1"
if /i "%CMD%"=="resume" (
    echo Resuming from last failure...
    powershell -ExecutionPolicy Bypass -File "run_release_pipeline_resumable.ps1" -Resume
    exit /b !errorlevel!
)

if /i "%CMD%"=="force" (
    echo Force restart - clearing checkpoint...
    powershell -ExecutionPolicy Bypass -File "run_release_pipeline_resumable.ps1" -Force
    exit /b !errorlevel!
)

if /i "%CMD%"=="status" (
    python "core\checkpoint_cli.py" status
    exit /b 0
)

if /i "%CMD%"=="log" (
    python "core\checkpoint_cli.py" log
    exit /b 0
)

if /i "%CMD%"=="reset" (
    python "core\checkpoint_cli.py" reset
    exit /b 0
)

echo Usage:
echo   run_release_pipeline.bat              - Run pipeline
echo   run_release_pipeline.bat resume       - Resume from last failure
echo   run_release_pipeline.bat force        - Force restart
echo   run_release_pipeline.bat status       - Show status
echo   run_release_pipeline.bat log          - Show execution log
echo   run_release_pipeline.bat reset        - Reset checkpoint

