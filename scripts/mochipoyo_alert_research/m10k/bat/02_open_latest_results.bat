@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10K\LATEST"
if not exist "%OUT%\99_UPLOAD_PACKAGE.zip" (
  echo [M10K BLOCKED] Result package not found:
  echo %OUT%\99_UPLOAD_PACKAGE.zip
  pause
  exit /b 2
)
start "" "%OUT%"
exit /b 0
