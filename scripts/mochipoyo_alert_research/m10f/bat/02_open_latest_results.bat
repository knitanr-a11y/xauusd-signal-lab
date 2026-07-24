@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10F\LATEST"
if not exist "%OUT%" (
  echo [M10F] LATEST output not found:
  echo %OUT%
  pause
  exit /b 2
)
start "" "%OUT%"
echo Opened: %OUT%
echo Submit 99_UPLOAD_PACKAGE.zip to ChatGPT.
pause
exit /b 0
