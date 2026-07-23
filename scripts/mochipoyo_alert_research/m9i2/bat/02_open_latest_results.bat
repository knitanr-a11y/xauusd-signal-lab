@echo off
setlocal
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9I2\LATEST"
if not exist "%OUT%" (
  echo [M9I2 BLOCKED] Latest result folder not found.
  pause
  exit /b 2
)
explorer "%OUT%"
exit /b 0
