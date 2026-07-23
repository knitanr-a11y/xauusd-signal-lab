@echo off
setlocal
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8BZ\LATEST"
if not exist "%LATEST%" (
  echo [STOP] M8BZ LATEST does not exist. Run 01_run_pullback_state_feature_audit.bat first.
  pause
  exit /b 2
)
start "" "%LATEST%"
exit /b 0
