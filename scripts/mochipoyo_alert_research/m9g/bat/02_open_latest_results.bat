@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9G\LATEST"

if not exist "%OUT%" (
  echo [M9G BLOCKED] LATEST output folder not found:
  echo %OUT%
  pause
  exit /b 2
)

start "" explorer "%OUT%"
echo [M9G OPENED] %OUT%
echo Submit 99_UPLOAD_PACKAGE.zip to ChatGPT.
pause
exit /b 0
