@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W10 M10P / M10P2 Runtime Freshness Diagnostic - READ ONLY
echo ============================================================
echo.
echo Do NOT run M10P BAT01 or M10P2 BAT01.
echo Do NOT delete lock files.
echo Do NOT restart BAT03 until this diagnostic package is reviewed.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E unchanged.
echo.

python "scripts\mochipoyo_alert_research\m10w10\python\run_m10w10_runtime_freshness_diagnostic.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10W10 diagnostic was BLOCKED.
  echo Do NOT reset or reinitialize M10P/M10P2 to force a pass.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W10\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W10 DIAGNOSTIC COMPLETE]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W10 LATEST folder.
echo Do NOT restart M10P/M10P2 yet.
pause
exit /b 0
