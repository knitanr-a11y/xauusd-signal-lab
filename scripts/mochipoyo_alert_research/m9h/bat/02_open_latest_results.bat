@echo off
setlocal
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9H\LATEST"
if not exist "%OUT%" (
  echo [M9H OPEN BLOCKED] LATEST output folder does not exist:
  echo %OUT%
  pause
  exit /b 2
)
explorer "%OUT%"
exit /b 0
