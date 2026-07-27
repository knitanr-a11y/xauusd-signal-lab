@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W17 NEITHER Regime Directional Opportunity Audit

echo ============================================================
echo Keep all existing forward monitors running unchanged.
echo This stage evaluates only the fixed M10W14 NEITHER regime buckets.
echo It does not modify any existing formula, threshold, start, runtime, or monitor.
echo.
python "scripts\mochipoyo_alert_research\m10w17\python\run_m10w17_neither_regime_directional_opportunity_audit.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10W17 BLOCKED. Do not alter bucket cuts or force a pass.
  pause
  exit /b %RC%
)
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W17\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W17 COMPLETE]
echo Upload only 99_UPLOAD_PACKAGE.zip from the M10W17 LATEST folder.
pause
exit /b 0
