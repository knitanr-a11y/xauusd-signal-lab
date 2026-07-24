@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."
echo ============================================================
echo M9Y GOLD Payoff Fresh Prospective Shadow - PERSISTENT
echo ============================================================
echo Keep this window OPEN. Keep M8C / M7C / collector / M9V running in parallel.
echo Audit-only: Discord OFF / MT5 orders OFF / live gate OFF.
echo Stop safely with 04_stop_shadow_forever.bat.
echo.
python "scripts\mochipoyo_alert_research\m9y\python\run_m9y_shadow_forever_safe.py"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo [M9Y LOOP STOPPED] normal stop.) else (echo [M9Y LOOP BLOCKED] exit code %RC%. Send full output to ChatGPT.)
echo Existing M8C/M7C/M9V remain unchanged.
pause
exit /b %RC%
