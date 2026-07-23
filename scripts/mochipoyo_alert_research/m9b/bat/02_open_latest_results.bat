@echo off
setlocal
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9B\LATEST"
if not exist "%OUT%" (
  echo [STOP] M9B LATEST does not exist. Run 01_run_genuine_primary_expanded_context_audit.bat first.
  pause
  exit /b 2
)
explorer "%OUT%"
exit /b 0
