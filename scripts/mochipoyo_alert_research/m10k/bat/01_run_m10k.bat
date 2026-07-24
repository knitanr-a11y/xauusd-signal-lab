@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10K M15 SHORT Exit / Loss-Tail Audit
echo HISTORICAL AUDIT ONLY - ENTRY TRIGGER FROZEN
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E running unchanged.
echo M10J C0212 entry formula is fixed; only TP / SL / max-hold exits are varied.
echo.
python "scripts\mochipoyo_alert_research\m10k\python\run_m10k.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10K was BLOCKED. Do not modify thresholds, hashes, forward starts, or running monitors.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)
echo [M10K PASS] Historical exit/loss-tail audit completed.
echo Run 02_open_latest_results.bat and upload only 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
