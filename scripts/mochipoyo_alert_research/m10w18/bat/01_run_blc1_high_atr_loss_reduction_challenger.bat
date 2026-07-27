@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W18 BLC1 High-ATR Loss Reduction Challenger - AUDIT ONLY
echo ============================================================
echo.
echo Existing forward monitors remain unchanged.
echo This is a post-hoc research-exposed historical challenger.
echo It does NOT authorize live/fresh adoption by historical results alone.
echo.
python "scripts\mochipoyo_alert_research\m10w18\python\run_m10w18_blc1_high_atr_loss_reduction_challenger.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10W18 BLOCKED. Do not modify the gate or threshold to force a pass.
  pause
  exit /b %RC%
)
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W18\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W18 COMPLETE]
echo Upload only 99_UPLOAD_PACKAGE.zip from M10W18 LATEST.
pause
exit /b 0
