@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10J Independent M15 SHORT Causal Feature Mining
echo HISTORICAL AUDIT ONLY - DO NOT TOUCH FORWARD MONITORS
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E running unchanged.
echo 2023-2024 generates and ranks formulas. 2025 and 2026 remain locked validation/test.
echo.

if not exist "scripts\mochipoyo_alert_research\m10j\python\run_m10j.py" (
  echo [M10J BLOCKED] Required script is missing.
  echo [SAFE] Do not modify forward monitors or thresholds.
  pause
  exit /b 2
)

python "scripts\mochipoyo_alert_research\m10j\python\run_m10j.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10J was BLOCKED. Do not modify thresholds, hashes, forward starts, or running monitors.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)
echo [M10J PASS] Historical causal feature mining completed.
echo Run 02_open_latest_results.bat and upload only 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
