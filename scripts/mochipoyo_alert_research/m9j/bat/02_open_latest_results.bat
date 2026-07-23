@echo off
setlocal
set "TARGET=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9J\LATEST"
if not exist "%TARGET%" (
  echo [M9J BLOCKED] LATEST output folder not found:
  echo %TARGET%
  pause
  exit /b 2
)
explorer "%TARGET%"
exit /b 0
