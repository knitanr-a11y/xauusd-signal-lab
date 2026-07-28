@echo off
setlocal EnableExtensions DisableDelayedExpansion

if defined LOCALAPPDATA (
  set "LATEST_DIR=%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\LATEST"
) else (
  set "LATEST_DIR=%TEMP%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\LATEST"
)

if not exist "%LATEST_DIR%" (
  echo [BTC_ML_V1_01] ERROR: LATEST does not exist.
  echo [BTC_ML_V1_01] Run 01_run_availability_audit.bat once, then run 02 again.
  echo [BTC_ML_V1_01] Expected: %LATEST_DIR%
  echo [BTC_ML_V1_01] This window will remain open.
  echo.
  pause
  exit /b 2
)

start "" explorer.exe "%LATEST_DIR%"
set "OPEN_EXIT_CODE=%ERRORLEVEL%"

if not "%OPEN_EXIT_CODE%"=="0" (
  echo [BTC_ML_V1_01] ERROR: Explorer could not open the LATEST folder.
  echo [BTC_ML_V1_01] Open this path manually: %LATEST_DIR%
  echo [BTC_ML_V1_01] This window will remain open.
  echo.
  pause
  exit /b %OPEN_EXIT_CODE%
)

echo [BTC_ML_V1_01] Opened: %LATEST_DIR%
exit /b 0
