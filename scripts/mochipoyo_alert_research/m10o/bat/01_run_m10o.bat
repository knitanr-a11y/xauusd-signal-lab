@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10O C056 + G013 Deterministic Reproduction
echo HISTORICAL AUDIT ONLY - DO NOT TOUCH FORWARD MONITORS
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E running unchanged.
echo Rebuild exact C056 + G013 from frozen raw GOLD data. No M10N result CSV is used to generate trades.
echo.

python "scripts\mochipoyo_alert_research\m10o\python\run_m10o.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10O was BLOCKED. Do not modify thresholds, hashes, forward starts, or running monitors.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)
echo [M10O PASS] Deterministic reproduction completed.
echo Run 02_open_latest_results.bat and upload only 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
