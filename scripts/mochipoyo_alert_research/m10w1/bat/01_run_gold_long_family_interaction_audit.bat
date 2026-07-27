@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W1 GOLD LONG Family Interaction Audit - READ ONLY
echo ============================================================
echo.
echo GOLD/XAUUSD LONG historical references only.
echo No SHORT ledgers and no M10P/M10P2 fresh outcomes are read.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 running unchanged.
echo.
python "scripts\mochipoyo_alert_research\m10w1\python\run_m10w1_gold_long_family_interaction_audit.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10W1 audit was BLOCKED.
  echo Do NOT alter M10A ledgers or running forward monitors to force a pass.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W1\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W1 PASS]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W1 LATEST folder.
pause
exit /b 0
