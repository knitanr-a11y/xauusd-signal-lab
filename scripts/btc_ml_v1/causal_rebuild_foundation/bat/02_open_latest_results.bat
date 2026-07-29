@echo off
setlocal EnableExtensions DisableDelayedExpansion
if defined LOCALAPPDATA (
  set "LATEST_DIR=%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\04_bar_time_semantics_rebuild_foundation\LATEST"
) else (
  set "LATEST_DIR=%TEMP%\xauusd_signal_lab\btc_ml_v1\outputs\04_bar_time_semantics_rebuild_foundation\LATEST"
)
set "UPLOAD_ZIP=%LATEST_DIR%\99_UPLOAD_PACKAGE.zip"
if exist "%UPLOAD_ZIP%" (
  start "" explorer.exe /select,"%UPLOAD_ZIP%"
  exit /b 0
)
if exist "%LATEST_DIR%" (
  start "" explorer.exe "%LATEST_DIR%"
  exit /b 0
)
echo [BTC_FF04] LATEST does not exist. Run 01 first.
pause
exit /b 2
