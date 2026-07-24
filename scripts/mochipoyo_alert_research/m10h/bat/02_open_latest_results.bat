@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10H\LATEST"
if not exist "%OUT%" (
  echo [ERROR] M10H LATEST folder not found: %OUT%
  pause
  exit /b 2
)
explorer "%OUT%"
echo.
echo Submit ONLY: %OUT%\99_UPLOAD_PACKAGE.zip
pause
exit /b 0
