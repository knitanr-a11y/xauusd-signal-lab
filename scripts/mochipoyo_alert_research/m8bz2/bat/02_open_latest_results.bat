@echo off
setlocal
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8BZ2\LATEST"
if not exist "%LATEST%" (
  echo [STOP] M8BZ2 LATEST does not exist. Run 01_run_multitimeframe_rci_context_audit.bat first.
  pause
  exit /b 2
)
start "" "%LATEST%"
exit /b 0
