@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."
echo ============================================================
echo M10B GOLD Multi-Timeframe Payoff Fresh Runtime Init - ONE TIME ONLY
echo ============================================================
echo Keep collector / M7C / M8C / M9V / M9Y RUNNING unchanged.
echo M10B is NEW and separate. It does NOT reset or backfill M9V/M9Y.
echo.
echo Run this only until [M10B INIT PASS]. After PASS NEVER run 01 again.
echo.
python "scripts\mochipoyo_alert_research\m10b\python\m10b_runtime.py" init
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10B fresh-start initialization was blocked.
  echo Do not delete/reset anything. Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)
echo.
echo [DONE] M10B fresh start frozen. NEXT: run 02_run_shadow_once.bat once.
pause
exit /b 0
