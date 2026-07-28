@echo off
setlocal EnableExtensions DisableDelayedExpansion

if defined LOCALAPPDATA (
  set "LATEST_DIR=%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\LATEST"
) else (
  set "LATEST_DIR=%TEMP%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\LATEST"
)

if not exist "%LATEST_DIR%" (
  echo [BTC_ML_V1_01] LATEST does not exist.
  echo [BTC_ML_V1_01] Run 01_run_availability_audit.bat once, then run 02 again.
  exit /b 2
)

start "" explorer.exe "%LATEST_DIR%"
echo [BTC_ML_V1_01] Opened: %LATEST_DIR%
exit /b 0
