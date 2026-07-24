@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "TARGET=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9X\LATEST"

echo ============================================================
echo M9X Latest Results Folder
echo ============================================================
echo %TARGET%
echo.

if not exist "%TARGET%" (
  echo [MISSING] M9X LATEST folder does not exist yet.
  echo Run 01_run_gold_payoff_decoupling_reproduction.bat first.
  pause
  exit /b 2
)

start "" explorer "%TARGET%"
echo [OPENED] Submit 99_UPLOAD_PACKAGE.zip to ChatGPT.
pause
exit /b 0
