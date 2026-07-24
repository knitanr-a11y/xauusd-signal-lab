@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M9V GOLD Multi-Timeframe Prospective Shadow - ONE SHOT AUDIT
echo ============================================================
echo.
echo Keep M8C / M7C / genuine source collector RUNNING unchanged.
echo Run this after 01_initialize_fresh_runtime_once.bat has PASSed.
echo Do not run this at the same time as the M9V forever loop.
echo.

python "scripts\mochipoyo_alert_research\m9v\python\run_m9v_shadow_once.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [STOP] M9V one-shot audit was blocked.
  echo M8C, M7C, and collector remain unchanged.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [DONE] M9V one-shot audit completed.
echo Open 05_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip to ChatGPT before starting the persistent loop.
pause
exit /b 0
