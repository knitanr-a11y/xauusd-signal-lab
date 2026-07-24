@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "TARGET=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9V\LATEST"

echo ============================================================
echo M9V Latest Results Folder
echo ============================================================
echo %TARGET%
echo.

if not exist "%TARGET%" (
  echo [MISSING] M9V LATEST folder does not exist yet.
  echo Run 02_run_shadow_once.bat after successful initialization.
  pause
  exit /b 2
)

start "" explorer "%TARGET%"
echo [OPENED] Submit 99_UPLOAD_PACKAGE.zip when ChatGPT asks for the current M9V checkpoint.
pause
exit /b 0
