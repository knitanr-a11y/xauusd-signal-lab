@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W25B\LATEST"
if not exist "%LATEST%" (
  echo [M10W25B] LATEST output does not exist yet.
  pause
  exit /b 2
)
start "" explorer "%LATEST%"
exit /b 0
