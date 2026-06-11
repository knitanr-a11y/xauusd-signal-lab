@echo off
setlocal EnableExtensions
set "D=%~dp0"
cd /d "%D%\..\..\.."
set "R=%CD%"
set "F="
if exist "%R%\..\..\goldsharp_m15.csv" set "F=%R%\..\.."
if "%F%"=="" if exist "%R%\..\goldsharp_m15.csv" set "F=%R%\.."
if "%F%"=="" if exist "%R%\Files\goldsharp_m15.csv" set "F=%R%\Files"
if "%F%"=="" if exist "%R%\goldsharp_m15.csv" set "F=%R%"
if "%F%"=="" if exist "%R%\..\FX_OUTPUTS\gold_v3" set "F=%R%\.."
if "%F%"=="" exit /b 1
for %%I in ("%F%") do set "F=%%~fI"
python "%R%\scripts\gold_v3_runtime\gold_v3_99_recent_closed_candle_signal_replay_audit.py" --candle-dir "%F%" --bars 128
set "E=%ERRORLEVEL%"
echo.
echo Paste: %F%\FX_OUTPUTS\gold_v3\99c\paste_me.txt
pause
exit /b %E%
