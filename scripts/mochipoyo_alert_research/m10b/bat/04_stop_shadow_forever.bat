@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."
echo ============================================================
echo M10B Graceful Stop Request

echo This stops M10B only. It does not stop/reset M9V or M9Y.
echo ============================================================
python "scripts\mochipoyo_alert_research\m10b\python\m10b_runtime.py" stop
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo [STOP REQUEST FAILED]
  pause
  exit /b %RC%
)
echo [DONE] Stop request written. The M10B loop will exit after the current cycle.
pause
exit /b 0
