@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W19 BLC1 ATR Filter Fresh Shadow - INITIALIZE ONCE ONLY
echo ============================================================
echo.
echo This creates a NEW immutable prospective start from the current stable GOLD M1 frontier.
echo It does NOT modify M9V/M9Y/M10B/M10E/M10P/M10P2 or any existing monitor.
echo Run this BAT exactly ONCE. After INIT PASS, NEVER run this BAT again.
echo.

python "scripts\mochipoyo_alert_research\m10w19\python\m10w19_runtime.py" initialize
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10W19 initialization blocked. Do not delete runtime files or force a new start.
  pause
  exit /b %RC%
)

echo.
echo [M10W19 INIT COMPLETE]
echo Next run 03_run_shadow_forever.bat and keep it open.
pause
exit /b 0
