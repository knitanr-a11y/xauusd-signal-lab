@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W0 GOLD LONG Reference Inventory - READ ONLY
echo ============================================================
echo.
echo GOLD/XAUUSD only. BTC is NOT in scope.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 running unchanged.
echo This does NOT modify any forward runtime, start, threshold, ledger, or monitor.
echo.

python "scripts\mochipoyo_alert_research\m10w0\python\run_m10w0_gold_long_reference_inventory.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10W0 inventory was BLOCKED.
  echo Do NOT change or delete M10A/M10P/M10P2 files to force a pass.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W0\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W0 PASS]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W0 LATEST folder.
echo Keep all forward monitors running unchanged.
pause
exit /b 0
