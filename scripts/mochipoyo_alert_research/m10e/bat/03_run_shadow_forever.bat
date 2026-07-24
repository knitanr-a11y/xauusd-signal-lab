@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10E H1 Baseline vs Compound-Filter Shadow - FOREVER
echo AUDIT ONLY - PRESERVE FROZEN START
necho ============================================================
echo.
echo Start this only after the first M10E bootstrap package is reviewed.
python "scripts\mochipoyo_alert_research\m10e\python\m10e_runtime.py" forever
set "RC=%ERRORLEVEL%"
echo.
echo M10E loop exited with code %RC%.
if not "%RC%"=="0" echo Send the full screen output to ChatGPT. Do NOT reinitialize.
pause
exit /b %RC%
