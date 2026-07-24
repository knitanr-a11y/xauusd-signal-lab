@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10P C056 + G013 Fresh Prospective Shadow - FOREVER
echo AUDIT ONLY - PRESERVE FROZEN START
echo ============================================================
echo.
echo Start this ONLY after ChatGPT reviews the M10P bootstrap package.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E running unchanged.
echo Do NOT rerun BAT01.
echo.

python "scripts\mochipoyo_alert_research\m10p\python\m10p_guarded_runtime.py" forever
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10P loop was BLOCKED. Do NOT reset/reinitialize anything.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)

echo [DONE] M10P loop stopped gracefully.
pause
exit /b 0
