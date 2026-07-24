@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10E H1 Compound-Loss Filter Fresh Prospective Init
echo AUDIT ONLY - NEW INDEPENDENT START - NO BACKFILL
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B running unchanged.
echo Run this BAT only until [M10E INIT PASS].
echo After INIT PASS, NEVER run this BAT again.
echo.
python "scripts\mochipoyo_alert_research\m10e\python\m10e_runtime.py" init
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10E initialization was BLOCKED.
  echo Do NOT delete or reset any runtime/start/lock.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)
echo.
echo [DONE] M10E fresh runtime initialized.
echo NEVER run BAT01 again.
echo NEXT: run 02_run_shadow_once.bat exactly once.
pause
exit /b 0
