@echo off
setlocal
for %%I in ("%~dp0\..\..\..") do set "REPO_ROOT=%%~fI"
set "OUTPUT_DIR=%REPO_ROOT%\outputs\btc_ml_v1\BCR13_b3_outcome_blind_density_audit\latest"
if not exist "%OUTPUT_DIR%" (
  echo No BCR13 latest output directory exists yet.
  exit /b 1
)
start "" "%OUTPUT_DIR%"
