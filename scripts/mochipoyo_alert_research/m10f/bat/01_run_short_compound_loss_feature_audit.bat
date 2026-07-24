@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10F SHORT Compound-Loss Feature Audit
echo HISTORICAL AUDIT ONLY - TARGET PF 2 - NO FORWARD CHANGE
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E running unchanged.
echo This reads only frozen hashed 2023-2026 GOLD research CSVs.
echo SHORT rules are discovered from 2023-2024 only.
echo 2025 is validation; 2026 through June 19 is final test.
echo It does NOT reset/backfill/modify any forward monitor.
echo.

python "scripts\mochipoyo_alert_research\m10f\python\run_short_compound_loss_feature_audit.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [STOP] M10F historical audit was BLOCKED.
  echo Do NOT alter M10B/M10E or any frozen start.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [DONE] M10F historical SHORT audit PASS.
echo NEXT: run 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip.
echo No SHORT forward arm is authorized by this PASS alone.
pause
exit /b 0
