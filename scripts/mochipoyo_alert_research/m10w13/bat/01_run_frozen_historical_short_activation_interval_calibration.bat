@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W13 Frozen Historical SHORT Activation Interval Calibration
echo AUDIT ONLY - NO OUTCOME / NO THRESHOLD REFIT
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 running unchanged.
echo Do NOT run M10P BAT01 or M10P2 BAT01.
echo This stage reads only frozen 2023-2026 GOLD OHLC/indicator context and does not read trade outcomes.
echo.

python "scripts\mochipoyo_alert_research\m10w13\python\run_m10w13_frozen_historical_short_activation_interval_calibration.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10W13 was BLOCKED.
  echo Do NOT modify frozen data, thresholds, starts, or runtimes to force a pass.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W13\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W13 COMPLETE]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W13 LATEST folder.
pause
exit /b 0
