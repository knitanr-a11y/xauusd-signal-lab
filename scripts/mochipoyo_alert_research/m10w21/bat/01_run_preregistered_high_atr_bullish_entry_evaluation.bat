@echo off
setlocal
cd /d "%~dp0\..\..\..\.."

echo M10W21 preregistered HIGH-ATR bullish entry evaluation - AUDIT ONLY

echo Keep all existing forward monitors unchanged, including M10W19.
echo Never rerun M10W19 BAT01.
echo.

python "scripts\mochipoyo_alert_research\m10w21\python\run_m10w21_preregistered_high_atr_bullish_entry_evaluation.py"
set RC=%ERRORLEVEL%
if not "%RC%"=="0" (
  echo M10W21 BLOCKED. Do not change frozen formulas. Send the console output to ChatGPT.
  pause
  exit /b %RC%
)

set LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W21\LATEST
if exist "%LATEST%" start "" explorer "%LATEST%"
echo M10W21 COMPLETE. Upload 99_UPLOAD_PACKAGE.zip from M10W21 LATEST.
pause
exit /b 0
