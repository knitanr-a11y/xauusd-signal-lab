@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10P1 C0212 Deterministic Reproduction
echo HISTORICAL AUDIT ONLY - M10P MUST KEEP RUNNING UNCHANGED
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P running unchanged.
echo Rebuild exact C0212 from frozen raw GOLD data. No result CSV is used to generate trades.
echo.

python "scripts\mochipoyo_alert_research\m10p1\python\run_m10p1.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10P1 was BLOCKED. Do not modify thresholds, frozen starts, or any running monitor.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)

echo [M10P1 PASS] C0212 deterministic reproduction completed.
echo Run 02_open_latest_results.bat and upload only 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
