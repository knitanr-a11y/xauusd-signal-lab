@echo off
setlocal EnableExtensions
set "TARGET=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9K\LATEST"
if not exist "%TARGET%" (
  echo [M9K BLOCKED] LATEST results folder not found:
  echo %TARGET%
  pause
  exit /b 2
)
start "" "%TARGET%"
exit /b 0
