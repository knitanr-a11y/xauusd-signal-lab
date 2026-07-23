@echo off
set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9I\LATEST"
if not exist "%OUT%" goto missing
start "" "%OUT%"
exit /b 0
:missing
echo [M9I BLOCKED] LATEST output folder does not exist.
pause
exit /b 2
