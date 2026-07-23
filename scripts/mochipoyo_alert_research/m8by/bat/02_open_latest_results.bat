@echo off
setlocal
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8BY\LATEST"
if not exist "%LATEST%" (
  echo [STOP] M8BY LATEST does not exist. Run 01_run_pullback_entry_opportunity_audit.bat first.
  pause
  exit /b 2
)
start "" "%LATEST%"
exit /b 0
