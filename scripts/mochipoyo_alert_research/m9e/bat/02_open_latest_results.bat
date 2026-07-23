@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9E\LATEST"
set "UPLOAD=%LATEST%\99_UPLOAD_PACKAGE.zip"

echo ============================================================
echo M9E Latest Results
echo ============================================================
echo Folder:
echo %LATEST%
echo.
echo Submit this file to ChatGPT:
echo %UPLOAD%
echo.

if exist "%LATEST%" (
  start "" "%LATEST%"
) else (
  echo [ERROR] M9E LATEST folder does not exist yet.
)

pause
exit /b 0
