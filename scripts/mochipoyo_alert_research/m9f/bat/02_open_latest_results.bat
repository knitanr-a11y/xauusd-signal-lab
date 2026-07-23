@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9F\LATEST"

if not exist "%OUT%" (
  echo [M9F BLOCKED] LATEST output folder does not exist:
  echo %OUT%
  pause
  exit /b 2
)

start "" explorer.exe "%OUT%"
echo.
echo Submit only 99_UPLOAD_PACKAGE.zip from this folder.
pause
exit /b 0
