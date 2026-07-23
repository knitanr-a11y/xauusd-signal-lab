@echo off
setlocal
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8B\LATEST"
if not exist "%LATEST%" (
  echo [STOP] M8B LATEST does not exist. Run 01_run_outcome_audit.bat first.
  pause
  exit /b 2
)
start "" explorer.exe "%LATEST%"
exit /b 0
