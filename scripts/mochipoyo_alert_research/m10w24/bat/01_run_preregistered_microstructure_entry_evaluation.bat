@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

python "scripts\mochipoyo_alert_research\m10w24\python\run_m10w24_preregistered_microstructure_entry_evaluation.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10W24 was BLOCKED. Do not alter frozen hypotheses or thresholds.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W24\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W24 COMPLETE]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W24 LATEST folder.
pause
exit /b 0
