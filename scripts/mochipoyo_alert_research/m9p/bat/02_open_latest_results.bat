@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "TARGET=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9P\LATEST"
if not exist "%TARGET%" (
  echo [M9P BLOCKED] LATEST output folder does not exist:
  echo %TARGET%
  pause
  exit /b 2
)
start "" "%TARGET%"
exit /b 0
