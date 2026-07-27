@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W3 GOLD LONG Baseline vs Filtered H1 Portfolio - READ ONLY
echo ============================================================
echo.
echo GOLD/XAUUSD only. No SHORT ledgers and no fresh outcomes are used for selection.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 running unchanged.
echo This does NOT modify any forward runtime, start, threshold, ledger, or monitor.
echo.

python "scripts\mochipoyo_alert_research\m10w3\python\run_m10w3_gold_long_baseline_vs_filtered_h1_portfolio_audit.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10W3 was BLOCKED.
  echo Do NOT edit M10A/M10D source ledgers, thresholds, or running monitors to force a pass.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W3\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W3 PASS]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W3 LATEST folder.
echo Keep all forward monitors running unchanged.
pause
exit /b 0
