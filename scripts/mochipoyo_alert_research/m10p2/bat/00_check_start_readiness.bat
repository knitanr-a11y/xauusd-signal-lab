@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10P2 C0212 Fresh Shadow - READ-ONLY START READINESS CHECK
echo ============================================================
echo.
echo Safe to rerun. This does NOT create or modify any M10P2 runtime/start/state.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P running unchanged.
echo.

python "scripts\mochipoyo_alert_research\m10p2\python\check_m10p2_start_readiness.py"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [READY] Now run 01_initialize_fresh_shadow.bat exactly once.
  pause
  exit /b 0
)
if "%RC%"=="3" (
  echo [WAIT] Do not run BAT01 yet. No newer CLOSED M1 exists.
  pause
  exit /b 0
)
echo [STOP] Readiness check was blocked. Send the complete console output to ChatGPT.
pause
exit /b %RC%
