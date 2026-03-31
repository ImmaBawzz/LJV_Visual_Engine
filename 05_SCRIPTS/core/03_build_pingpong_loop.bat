@echo off
setlocal
set "ROOT=%~dp0..\.."
set "FFMPEG=C:\ffmpeg\bin\ffmpeg.exe"
set "VIDEO=%ROOT%\02_INPUT\video\clip.mp4"
set "OUTPUT=%ROOT%\03_WORK\loops\loop_pingpong.mp4"
if not exist "%FFMPEG%" ( echo ffmpeg missing & exit /b 1 )
if not exist "%VIDEO%" ( echo clip missing & exit /b 1 )
"%FFMPEG%" -y -i "%VIDEO%" -filter_complex "[0:v]fps=30,minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir,scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,split[f][s];[s]reverse[r];[f][r]concat=n=2:v=1:a=0,format=yuv420p[v]" -map "[v]" -an -c:v libx264 -preset medium -crf 18 "%OUTPUT%"
if errorlevel 1 ( echo pingpong failed & exit /b 1 )
echo Done: %OUTPUT%
endlocal
