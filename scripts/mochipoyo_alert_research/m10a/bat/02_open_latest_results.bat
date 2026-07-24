@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "TARGET=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10A\LATEST"

echo ============================================================
echo M10A Latest Results Folder
echo ============================================================
echo %TARGET%
echo.

if not exist "%TARGET%" (
  echo [MISSING] M10A LATEST folder does not exist yet.
  echo Run 01_run_gold_multitimeframe_payoff_reproduction.bat first.
  pause
  exit /b 2
)

start "" explorer "%TARGET%"
echo [OPENED] Submit 99_UPLOAD_PACKAGE.zip to ChatGPT.
pause
exit /b 0
