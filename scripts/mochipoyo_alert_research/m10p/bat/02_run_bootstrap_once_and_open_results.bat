@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10P C056 + G013 Fresh Prospective Shadow - ONE CYCLE
 echo AUDIT ONLY - SAFE TO RERUN; DOES NOT RESET START
 echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E running unchanged.
echo.

python "scripts\mochipoyo_alert_research\m10p\python\m10p_runtime.py" once
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10P cycle was BLOCKED. Do NOT rerun BAT01.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10P\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10P BOOTSTRAP PASS]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10P LATEST folder.
echo Do NOT start BAT03 until the bootstrap package is reviewed.
pause
exit /b 0
