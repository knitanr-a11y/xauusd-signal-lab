@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10E\LATEST"
if not exist "%OUT%" (
  echo [STOP] M10E LATEST output not found:
  echo %OUT%
  pause
  exit /b 2
)
explorer "%OUT%"
echo.
echo Opened M10E LATEST.
echo Submit only 99_UPLOAD_PACKAGE.zip to ChatGPT.
pause
exit /b 0
