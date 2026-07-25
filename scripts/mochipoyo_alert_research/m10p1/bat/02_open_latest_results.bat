@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10P1\LATEST"

echo ============================================================
echo M10P1 C0212 Deterministic Reproduction - RESULTS
echo ============================================================
echo.
if not exist "%LATEST%" (
  echo [STOP] M10P1 LATEST folder not found:
  echo %LATEST%
  pause
  exit /b 2
)

start "" explorer "%LATEST%"
echo.
echo Upload only:
echo %LATEST%\99_UPLOAD_PACKAGE.zip
pause
exit /b 0
