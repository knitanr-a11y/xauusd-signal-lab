@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\..\.."

set "RAW_DIR=%~1"
set "CONFIG_PATH=%~2"
set "OUTPUT_DIR=outputs\gold_ml_v1\exploration_batch024_m15_h1_pullback"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

if "%RAW_DIR%"=="" (
  echo [FAIL] Frozen raw history directory was not supplied.
  >"%OUTPUT_DIR%\EXPLORATION_RUN_ERROR.txt" echo Missing raw history directory argument.
  exit /b 4
)
if "%CONFIG_PATH%"=="" set "CONFIG_PATH=config\gold_ml_v1\exploration_batch024_m15_h1_pullback_20260625.json"

set "PYTHON_CMD="
if exist ".venv_batch023_bridge\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023_bridge\Scripts\python.exe"
if not defined PYTHON_CMD if exist ".venv_batch023\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023\Scripts\python.exe"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  echo [FAIL] Python 3.12 could not be found.
  >"%OUTPUT_DIR%\EXPLORATION_RUN_ERROR.txt" echo Python 3.12 could not be found.
  exit /b 4
)

for %%F in (gold_v3_2023_2026_m1.csv gold_v3_2023_2026_m15.csv gold_v3_2023_2026_h1.csv) do (
  if not exist "%RAW_DIR%\%%F" (
    echo [FAIL] Missing frozen exploration input: %%F
    >"%OUTPUT_DIR%\EXPLORATION_RUN_ERROR.txt" echo Missing %RAW_DIR%\%%F
    exit /b 4
  )
)

if not exist "%CONFIG_PATH%" (
  echo [FAIL] Frozen Batch024 exploration config is missing.
  >"%OUTPUT_DIR%\EXPLORATION_RUN_ERROR.txt" echo Missing %CONFIG_PATH%
  exit /b 4
)

echo ============================================================
echo GOLD_ML_V1 - EXPLORATION BATCH024 AUDIT ONLY
echo New lineage: H1 trend plus M15 pullback re-entry
echo 36 predeclared cells; existing frozen nine unchanged
echo 2023 exploration / 2024 validation / 2025 final / 2026 diagnostic
echo ============================================================

%PYTHON_CMD% scripts\gold_ml_v1\exploration\run_batch024_pullback_exploration.py ^
  --raw-dir "%RAW_DIR%" ^
  --config "%CONFIG_PATH%" ^
  --output-dir "%OUTPUT_DIR%"
set "RC=%ERRORLEVEL%"

if "%RC%"=="0" (
  echo [PASS] Batch024 exploration reports completed.
) else (
  echo [FAIL] Batch024 validation or report generation failed. Exit code: %RC%
  echo Check %OUTPUT_DIR%\LATEST_RUN_SUMMARY.txt and EXPLORATION_RUN_ERROR.txt
)

exit /b %RC%
