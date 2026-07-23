@echo off
setlocal
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8A\LATEST"
if not exist "%LATEST%" (
  echo [STOP] M8A LATEST does not exist. Run 01 then 02 first.
  pause
  exit /b 2
)
start "" explorer.exe "%LATEST%"
exit /b 0
