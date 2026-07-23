@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9D\LATEST"

if not exist "%OUT%" (
  echo [M9D OPEN BLOCKED] LATEST output folder does not exist:
  echo %OUT%
  pause
  exit /b 2
)

start "" "%OUT%"
echo [M9D OPEN] %OUT%
echo Submit: 99_UPLOAD_PACKAGE.zip
pause
exit /b 0
