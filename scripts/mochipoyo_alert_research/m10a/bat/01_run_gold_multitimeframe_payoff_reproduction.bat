@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10A GOLD Multi-Timeframe Payoff Deterministic Reproduction
echo HISTORICAL AUDIT ONLY - M9V/M9Y REMAIN UNCHANGED
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y running unchanged.
echo This reads only the frozen hashed 2023-2026 GOLD research CSVs.
echo It does NOT backfill or modify M9V/M9Y.
echo It does NOT send Discord or MT5 orders.
echo.

python "scripts\mochipoyo_alert_research\m10a\python\run_gold_multitimeframe_payoff_reproduction.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [STOP] M10A deterministic reproduction was BLOCKED.
  echo Forward monitors remain unchanged.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [DONE] M10A deterministic reproduction PASS.
echo NEXT: run 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip to ChatGPT.
pause
exit /b 0
