@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W16 Preregistered Blind-Spot Trend Continuation Evaluation

echo GOLD / AUDIT ONLY

echo ============================================================
echo.
echo This evaluates ONLY the two formulas frozen in M10W15.
echo Do NOT alter thresholds or formulas after seeing the result.
echo Existing forward monitors remain running unchanged.
echo.
python "scripts\mochipoyo_alert_research\m10w16\python\run_m10w16_preregistered_blind_spot_trend_continuation_evaluation.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10W16 was BLOCKED. Do not force a pass or tune the formulas.
  pause
  exit /b %RC%
)
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W16\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W16 COMPLETE]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W16 LATEST folder.
pause
exit /b 0
