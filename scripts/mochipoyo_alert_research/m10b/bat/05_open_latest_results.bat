@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "TARGET=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10B\LATEST"
echo ============================================================
echo M10B Latest Results Folder

echo %TARGET%
echo ============================================================
if not exist "%TARGET%" (
  echo [MISSING] M10B LATEST folder does not exist yet.
  echo Run 02_run_shadow_once.bat after BAT01 INIT PASS.
  pause
  exit /b 2
)
start "" explorer "%TARGET%"
echo [OPENED] M10B latest results.
pause
exit /b 0
