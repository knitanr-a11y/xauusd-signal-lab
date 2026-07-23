@echo off
setlocal
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8BX\LATEST"
if not exist "%LATEST%" (
  echo [STOP] M8BX LATEST does not exist. Run 01_run_excursion_path_audit.bat first.
  pause
  exit /b 2
)
start "" explorer.exe "%LATEST%"
exit /b 0
