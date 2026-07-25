@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10P2 C0212 Fresh Prospective Shadow - ONE BOOTSTRAP CYCLE
echo AUDIT ONLY - SAFE TO RERUN; DOES NOT RESET START
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P running unchanged.
echo Do NOT rerun M10P2 BAT01.
echo.

python "scripts\mochipoyo_alert_research\m10p2\python\m10p2_runtime.py" once
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10P2 bootstrap cycle was BLOCKED. Do NOT rerun BAT01.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10P2\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10P2 BOOTSTRAP PASS]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10P2 LATEST folder.
echo Do NOT start BAT03 until the bootstrap package is reviewed.
pause
exit /b 0
