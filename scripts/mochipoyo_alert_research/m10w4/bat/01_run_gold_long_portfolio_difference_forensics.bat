@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W4 GOLD LONG Portfolio Difference Forensics - READ ONLY
echo ============================================================
echo.
echo GOLD/XAUUSD only. No threshold search. No SHORT/fresh outcomes.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 running unchanged.
echo.

python "scripts\mochipoyo_alert_research\m10w4\python\run_m10w4_gold_long_portfolio_difference_forensics.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10W4 was BLOCKED.
  echo Do NOT edit source ledgers, thresholds, starts, or running monitors to force a pass.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W4\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W4 PASS]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W4 LATEST folder.
echo Keep all forward monitors running unchanged.
pause
exit /b 0
