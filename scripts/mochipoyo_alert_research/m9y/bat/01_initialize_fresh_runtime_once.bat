@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."
echo ============================================================
echo M9Y GOLD Payoff Fresh Prospective Runtime Init - ONE TIME ONLY
echo ============================================================
echo Keep M8C / M7C / genuine source collector / M9V RUNNING unchanged.
echo M9Y is a NEW separate audit-only runtime. It does NOT reset or backfill M9V.
echo.
echo Run this only until [M9Y INIT PASS]. After PASS never run 01 again.
echo.
python "scripts\mochipoyo_alert_research\m9y\python\initialize_m9y_fresh_runtime_once.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
 echo.
 echo [STOP] M9Y fresh-start initialization was blocked.
 echo Do not delete/reset anything. Send the full screen output to ChatGPT.
 pause
 exit /b %RC%
)
echo.
echo [DONE] M9Y fresh start frozen. NEXT: run 02_run_shadow_once.bat once.
pause
exit /b 0
