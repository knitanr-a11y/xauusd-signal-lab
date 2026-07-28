@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W25B H4_S4 BOUNDARY / CAUSAL NEITHER CORRECTION - AUDIT ONLY
echo ============================================================
echo.
echo Keep all existing forward monitors including M10W19 BAT03 running unchanged.
echo This stage reads pre-entry coverage/features only and does not evaluate PF, PnL, win/loss, or future returns.
echo It does not create a new prospective start.
echo.

python "scripts\mochipoyo_alert_research\m10w25b\python\run_m10w25b_h4_s4_boundary_and_causal_neither_cohort_correction.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10W25B was BLOCKED.
  echo Do not force a pass, change thresholds, or create a fresh start.
  echo Upload the generated package and the full screen output.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W25B\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W25B COMPLETE]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W25B LATEST folder.
pause
exit /b 0
