@echo off
setlocal
set "P=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9Y\LATEST"
if not exist "%P%" (
 echo [M9Y] LATEST results not found: %P%
 pause
 exit /b 2
)
start "" explorer "%P%"
echo Submit 99_UPLOAD_PACKAGE.zip to ChatGPT when requested.
pause
