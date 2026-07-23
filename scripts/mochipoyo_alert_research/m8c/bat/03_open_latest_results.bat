@echo off
setlocal
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8C\LATEST"
if not exist "%LATEST%" (
  echo [STOP] M8C LATEST does not exist yet. Run 01 then start 02 first.
  pause
  exit /b 2
)
start "" explorer.exe "%LATEST%"
exit /b 0
