@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W19 BLC1 ATR Filter Fresh Shadow - FOREVER

echo ============================================================
echo.
echo Requires a successful one-time M10W19 initialization.
echo This is audit-only. No Discord send. No MT5 orders. No existing monitor changes.
echo Close with Ctrl+C only when intentionally stopping this new M10W19 shadow.
echo.

python "scripts\mochipoyo_alert_research\m10w19\python\m10w19_runtime.py" forever
set "RC=%ERRORLEVEL%"
echo.
echo [M10W19 EXIT] code=%RC%
pause
exit /b %RC%
