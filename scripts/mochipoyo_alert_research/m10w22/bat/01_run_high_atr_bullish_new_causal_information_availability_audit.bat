@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W22 HIGH-ATR BULLISH CAUSAL INFORMATION AUDIT - READ ONLY
echo ============================================================
echo Keep all existing forward monitors including M10W19 running unchanged.
echo This stage does not compute future returns, PF, PnL, win/loss labels, or outcome correlations.
echo.
python "scripts\mochipoyo_alert_research\m10w22\python\run_high_atr_bullish_new_causal_information_availability_audit.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo [STOP] M10W22 BLOCKED. Do not change thresholds or monitors.
  pause
  exit /b %RC%
)
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W22\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo [M10W22 COMPLETE] Upload only 99_UPLOAD_PACKAGE.zip from M10W22 LATEST.
pause
exit /b 0
