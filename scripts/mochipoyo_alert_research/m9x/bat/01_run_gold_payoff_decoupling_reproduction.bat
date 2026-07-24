@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M9X GOLD Payoff Decoupling Deterministic Reproduction

echo HISTORICAL AUDIT ONLY - NO M9V/M8C/M7C RESET

echo ============================================================
echo.
echo Keep M8C / M7C / genuine source collector / M9V v2 running unchanged.
echo This reads the frozen 2023-2026 GOLD research CSVs only.
echo It does NOT backfill or modify M9V and does NOT send Discord or MT5 orders.
echo.

python "scripts\mochipoyo_alert_research\m9x\python\run_gold_payoff_decoupling_reproduction.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [STOP] M9X deterministic reproduction was blocked.
  echo M8C, M7C, collector, and M9V remain unchanged.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [DONE] M9X deterministic reproduction PASS.
echo NEXT: run 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip to ChatGPT.
pause
exit /b 0
