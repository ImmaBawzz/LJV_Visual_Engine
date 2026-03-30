@echo off
setlocal
cd /d "%~dp0"
call "05_SCRIPTS\run_release_pipeline.bat" %*
exit /b %errorlevel%