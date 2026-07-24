@echo off
setlocal
cd /d "%~dp0\..\..\..\.."
python "scripts\mochipoyo_alert_research\m9y\python\stop_m9y_shadow_forever.py"
pause
