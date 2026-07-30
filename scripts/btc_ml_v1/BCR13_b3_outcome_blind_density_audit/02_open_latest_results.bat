@echo off
setlocal EnableExtensions DisableDelayedExpansion

if defined LOCALAPPDATA (
  set "LOCAL_ROOT=%LOCALAPPDATA%\xauusd_signal_lab"
) else (
  set "LOCAL_ROOT=%TEMP%\xauusd_signal_lab"
)

set "OUTPUT_DIR=%LOCAL_ROOT%\btc_ml_v1\outputs\BCR13_b3_outcome_blind_density_audit\LATEST"
set "UPLOAD_ZIP=%OUTPUT_DIR%\99_UPLOAD_PACKAGE.zip"

if exist "%UPLOAD_ZIP%" (
  start "" explorer.exe /select,"%UPLOAD_ZIP%"
  exit /b 0
)

if exist "%OUTPUT_DIR%" (
  start "" explorer.exe "%OUTPUT_DIR%"
  echo BCR13 output folder exists, but 99_UPLOAD_PACKAGE.zip is not present.
  pause
  exit /b 1
)

echo No BCR13 output directory exists yet:
echo %OUTPUT_DIR%
pause
exit /b 1
