@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W2 M10D H1 Filtered Reference Inventory - READ ONLY
echo ============================================================
echo.
echo GOLD/XAUUSD only. BTC is NOT in scope.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 running unchanged.
echo This reads only existing M10D local historical evidence.
echo It does NOT modify forward runtimes, starts, thresholds, or ledgers.
echo.

python "scripts\mochipoyo_alert_research\m10w2\python\run_m10w2_m10d_h1_filtered_reference_inventory.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10W2 inventory was BLOCKED.
  echo Do NOT change/delete/rebuild M10D or running monitor files to force a pass.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W2\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W2 PASS]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W2 LATEST folder.
echo Keep all forward monitors running unchanged.
pause
exit /b 0
