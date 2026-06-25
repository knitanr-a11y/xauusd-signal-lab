@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\..\.."

set "RAW_DIR=%~1"
set "BRIDGE_DIR=%~2"
set "CONFIG_PATH=%~3"
set "OUTPUT_DIR=outputs\gold_ml_v1\cost_stress_raw_reconstructed"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

if "%RAW_DIR%"=="" (
  echo [FAIL] RAW history directory was not supplied.
  >"%OUTPUT_DIR%\COST_STRESS_RUN_ERROR.txt" echo Missing RAW history directory argument.
  exit /b 4
)
if "%BRIDGE_DIR%"=="" (
  echo [FAIL] Warmup bridge output directory was not supplied.
  >"%OUTPUT_DIR%\COST_STRESS_RUN_ERROR.txt" echo Missing warmup bridge directory argument.
  exit /b 4
)
if "%CONFIG_PATH%"=="" set "CONFIG_PATH=config\gold_ml_v1\cost_stress_raw_reconstructed_20260625.json"

set "PYTHON_CMD="
if exist ".venv_batch023_bridge\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023_bridge\Scripts\python.exe"
if not defined PYTHON_CMD if exist ".venv_batch023\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023\Scripts\python.exe"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  echo [FAIL] Python 3.12 could not be found.
  >"%OUTPUT_DIR%\COST_STRESS_RUN_ERROR.txt" echo Python 3.12 could not be found.
  exit /b 4
)

if not exist "%RAW_DIR%\gold_v3_2023_2026_m1.csv" (
  echo [FAIL] Frozen M1 raw CSV is missing.
  >"%OUTPUT_DIR%\COST_STRESS_RUN_ERROR.txt" echo Missing %RAW_DIR%\gold_v3_2023_2026_m1.csv
  exit /b 4
)
if not exist "%BRIDGE_DIR%\warmup_bridge_summary.json" (
  echo [FAIL] Verified warmup bridge output is missing.
  >"%OUTPUT_DIR%\COST_STRESS_RUN_ERROR.txt" echo Missing %BRIDGE_DIR%\warmup_bridge_summary.json
  exit /b 4
)
if not exist "%CONFIG_PATH%" (
  echo [FAIL] Frozen cost-stress config is missing.
  >"%OUTPUT_DIR%\COST_STRESS_RUN_ERROR.txt" echo Missing %CONFIG_PATH%
  exit /b 4
)

echo ============================================================
echo GOLD_ML_V1 - COST STRESS AUDIT ONLY
echo RAW_RECONSTRUCTED primary / WARMUP_BRIDGE_EXACT separate
echo ============================================================

%PYTHON_CMD% scripts\gold_ml_v1\cost_stress\run_cost_stress_raw_reconstructed.py ^
  --raw-dir "%RAW_DIR%" ^
  --bridge-dir "%BRIDGE_DIR%" ^
  --config "%CONFIG_PATH%" ^
  --output-dir "%OUTPUT_DIR%"
set "RC=%ERRORLEVEL%"

if "%RC%"=="0" (
  echo [PASS] Cost-stress report completed. No automatic next phase was started.
) else (
  echo [FAIL] Cost-stress validation or report generation failed. Exit code: %RC%
  echo Check %OUTPUT_DIR%\LATEST_RUN_SUMMARY.txt and COST_STRESS_RUN_ERROR.txt
)

exit /b %RC%
