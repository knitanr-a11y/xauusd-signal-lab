@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10D H1 Compound-Loss Filter Deterministic Reproduction
echo HISTORICAL AUDIT ONLY - M9Y/M10B REMAIN UNCHANGED
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B running unchanged.
echo This reads only the frozen hashed 2023-2026 GOLD research CSVs.
echo It does NOT reset, backfill, or modify any forward monitor.
echo It does NOT send Discord or MT5 orders.
echo.

python "scripts\mochipoyo_alert_research\m10d\python\run_h1_compound_loss_filter_reproduction.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [STOP] M10D deterministic reproduction was BLOCKED.
  echo DO NOT reset M9Y or M10B and DO NOT change any frozen start.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [DONE] M10D deterministic reproduction PASS.
echo NEXT: run 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip to ChatGPT.
echo Do NOT create or start a new prospective filter monitor before package review.
pause
exit /b 0
