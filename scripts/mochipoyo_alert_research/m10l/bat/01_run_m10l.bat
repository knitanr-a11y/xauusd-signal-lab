@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10L H1 Mochipoyo-Independent SHORT Causal Feature Mining
echo HISTORICAL AUDIT ONLY - DO NOT TOUCH FORWARD MONITORS
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E running unchanged.
echo Candidate universe is all causal H1 decisions; M7C/M10J/M10K are not used as the H1 candidate universe.
echo.

python "scripts\mochipoyo_alert_research\m10l\python\run_m10l.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10L was BLOCKED. Do not modify thresholds, hashes, forward starts, or running monitors.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)
echo [M10L PASS] Historical H1 independent SHORT mining completed.
echo Run 02_open_latest_results.bat and upload only 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
