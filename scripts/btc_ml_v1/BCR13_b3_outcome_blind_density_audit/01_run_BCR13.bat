@echo off
setlocal EnableExtensions

set "STAGE_DIR=%~dp0"
for %%I in ("%STAGE_DIR%\..\..\..") do set "REPO_ROOT=%%~fI"
set "PY_SCRIPT=%STAGE_DIR%python\run_bcr13_b3_density_audit.py"
set "CONTRACT=%REPO_ROOT%\configs\btc_ml_v1\btc_bcr12_materially_new_outcome_blind_track_b_mechanism_design_contract_20260730.json"
set "DEFAULT_INPUT=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv"
set "OUTPUT_DIR=%REPO_ROOT%\outputs\btc_ml_v1\BCR13_b3_outcome_blind_density_audit\latest"

if defined BTC_BCR13_INPUT (
  set "INPUT=%BTC_BCR13_INPUT%"
) else (
  set "INPUT=%DEFAULT_INPUT%"
)

if not exist "%PY_SCRIPT%" (
  echo ERROR: Python script not found:
  echo   %PY_SCRIPT%
  exit /b 1
)
if not exist "%CONTRACT%" (
  echo ERROR: BCR12 contract not found:
  echo   %CONTRACT%
  exit /b 1
)
if not exist "%INPUT%" (
  echo ERROR: BTC M15 input not found:
  echo   %INPUT%
  echo Set BTC_BCR13_INPUT to the exact source path and rerun.
  exit /b 1
)

where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo ERROR: Python was not found in PATH.
    exit /b 1
  )
  set "PYTHON=python"
)

echo.
echo BCR13 label-free audit starting.
echo Input:  %INPUT%
echo Output: %OUTPUT_DIR%
echo.

%PYTHON% "%PY_SCRIPT%" ^
  --input "%INPUT%" ^
  --contract "%CONTRACT%" ^
  --output-dir "%OUTPUT_DIR%" ^
  --allow-prefix-rehydrate ^
  --repeat-check

if errorlevel 1 (
  echo.
  echo BCR13 FAILED. No fallback or alternative input was used.
  exit /b 1
)

echo.
echo BCR13 completed with deterministic repeat match.
echo Upload the ZIP, deterministic_repeat.json, and package_sha256.txt from:
echo   %OUTPUT_DIR%
echo.
exit /b 0
