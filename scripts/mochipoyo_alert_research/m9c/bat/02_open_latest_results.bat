@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9C\LATEST"

if not exist "%OUT%" (
  echo [M9C OPEN BLOCKED] Latest result folder does not exist:
  echo %OUT%
  pause
  exit /b 2
)

explorer "%OUT%"
exit /b 0
