@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10N Downside-Regime Specific SHORT Research
echo HISTORICAL AUDIT ONLY - DO NOT TOUCH FORWARD MONITORS
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E running unchanged.
echo Regime gates use 2023-2024 discovery only. 2025/2026 remain locked holdouts until gate freeze.
echo Exact C0212/C056/M5 seed formula features are excluded from regime-gate generation.
echo.

python "scripts\mochipoyo_alert_research\m10n\python\run_m10n.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10N was BLOCKED. Do not modify thresholds, hashes, forward starts, or running monitors.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)
echo [M10N PASS] Historical downside-regime SHORT research completed.
echo Run 02_open_latest_results.bat and upload only 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
