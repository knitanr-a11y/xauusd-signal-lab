@echo off
setlocal
set "ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"
set "REPO=%~dp0..\..\..\.."
set "SKELETON=%REPO%\config\mochipoyo_alert_research\m8b_frozen_trade_skeleton_20260723.csv"
set "OUTPUT=%ROOT%\outputs\M8B"
set "SCRIPT=%~dp0..\python\run_extra_signal_outcome_audit.py"

python "%SCRIPT%" --trade-skeleton "%SKELETON%" --output-root "%OUTPUT%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M8B outcome audit was blocked.
  echo Do not change M7C formulas, thresholds, runtime manifest, or prospective start.
  echo If the message says MT5 symbol is ambiguous, copy the displayed symbol names and send them to ChatGPT.
  pause
  exit /b %RC%
)
echo [OK] 01 complete. Run 02_open_latest_results.bat to open the result folder.
pause
exit /b 0
