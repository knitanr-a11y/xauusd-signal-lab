@echo off
setlocal
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9A\LATEST"
if not exist "%OUT%" (
  echo [STOP] M9A LATEST does not exist. Run 01_run_sample_expansion_availability_audit.bat first.
  pause
  exit /b 2
)
explorer "%OUT%"
exit /b 0
