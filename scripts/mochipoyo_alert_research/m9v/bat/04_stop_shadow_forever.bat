@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M9V GOLD Multi-Timeframe Prospective Shadow - SAFE STOP
echo ============================================================
echo.
echo This only requests the M9V loop to stop.
echo It does NOT stop or reset M8C, M7C, or the genuine source collector.
echo.

python "scripts\mochipoyo_alert_research\m9v\python\stop_m9v_shadow_forever.py"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo [DONE] M9V stop request written. The persistent M9V window should exit safely.
) else (
  echo [ERROR] M9V stop helper returned %RC%.
)
pause
exit /b %RC%
