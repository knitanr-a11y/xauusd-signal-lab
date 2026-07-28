@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

python "scripts\mochipoyo_alert_research\m10w24b\python\run_m10w24b_neither_cohort_scope_correction.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10W24B was BLOCKED. Do not alter the frozen cohort correction or hypotheses.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W24B\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W24B COMPLETE]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W24B LATEST folder.
pause
exit /b 0
