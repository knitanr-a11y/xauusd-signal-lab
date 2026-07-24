@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10G M15 SHORT Reclaim Audit
echo HISTORICAL AUDIT ONLY - KEEP M10B/M10E RUNNING UNCHANGED
echo ============================================================
echo.
echo This reads only frozen hashed GOLD research CSVs.
echo It does NOT reset, backfill, or modify any forward monitor.
echo It does NOT create a SHORT forward arm.
echo.

python "scripts\mochipoyo_alert_research\m10g\python\run_m15_short_reclaim_audit.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10G audit was BLOCKED.
  echo Keep M10B/M10E running and send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [DONE] M10G historical audit PASS.
echo NEXT: run 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
