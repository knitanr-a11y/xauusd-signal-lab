@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\..\.."

echo ============================================================
echo MOCHIPOYO - STOPPED FRESH LOOPS READ-ONLY DIAGNOSTIC
echo ============================================================
echo.
echo Targets: M9V M9Y M10B M10E M10P M10P2 M10W19
echo This BAT does NOT remove locks, restart loops, reset runtimes,
echo change prospective starts, alter state/history, or touch MT5 CSVs.
echo.

python "scripts\mochipoyo_alert_research\recovery\python\audit_stopped_fresh_loops.py"
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo [STOP] Diagnostic was BLOCKED.
  echo Do not delete locks or rerun any initializer.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\FRESH_LOOP_DIAGNOSTIC\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [DIAGNOSTIC COMPLETE]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened LATEST folder.
echo Do not run forced-reboot recovery until this diagnostic package is reviewed,
echo unless ChatGPT explicitly instructs you otherwise.
pause
exit /b 0
