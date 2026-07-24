@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10E H1 Baseline vs Compound-Filter Shadow - ONE SHOT
echo AUDIT ONLY - NO BACKFILL - NO LIVE PROMOTION
echo ============================================================
echo.
python "scripts\mochipoyo_alert_research\m10e\python\m10e_runtime.py" once
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10E one-shot was BLOCKED.
  echo Do NOT reinitialize M10E and do NOT reset M9V/M9Y/M10B.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)
echo.
echo [DONE] M10E one-shot PASS.
echo NEXT: run 05_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip.
echo DO NOT run 03_run_shadow_forever.bat until the bootstrap package is reviewed.
pause
exit /b 0
