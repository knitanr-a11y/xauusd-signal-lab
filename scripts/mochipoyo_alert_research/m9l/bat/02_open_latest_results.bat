@echo off
setlocal
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9L\LATEST"
if not exist "%OUT%" (
  echo [M9L] LATEST output folder not found:
  echo %OUT%
  pause
  exit /b 2
)
explorer "%OUT%"
exit /b 0
