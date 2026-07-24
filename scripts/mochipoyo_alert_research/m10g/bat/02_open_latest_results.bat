@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10G\LATEST"
if not exist "%OUT%" (
  echo [M10G] LATEST output folder not found: %OUT%
  pause
  exit /b 2
)
explorer "%OUT%"
echo.
echo Submit only 99_UPLOAD_PACKAGE.zip to ChatGPT.
pause
exit /b 0
