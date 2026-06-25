@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\..\.."

set "FILES_DIR=%~1"
set "CONFIG_PATH=%~2"
set "OUTPUT_DIR=outputs\gold_ml_v1\fresh_prospective_confirmation"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

if "%FILES_DIR%"=="" (
  echo [FAIL] MQL5 Files directory was not supplied.
  >"%OUTPUT_DIR%\FRESH_PROSPECTIVE_RUN_ERROR.txt" echo Missing MQL5 Files directory argument.
  exit /b 4
)
if "%CONFIG_PATH%"=="" set "CONFIG_PATH=config\gold_ml_v1\fresh_prospective_confirmation_20260625.json"

set "PYTHON_CMD="
if exist ".venv_batch023_bridge\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023_bridge\Scripts\python.exe"
if not defined PYTHON_CMD if exist ".venv_batch023\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023\Scripts\python.exe"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  echo [FAIL] Python 3.12 could not be found.
  >"%OUTPUT_DIR%\FRESH_PROSPECTIVE_RUN_ERROR.txt" echo Python 3.12 could not be found.
  exit /b 4
)

for %%F in (goldsharp_m1.csv goldsharp_m15.csv goldsharp_h1.csv goldsharp_h4.csv goldsharp_d1.csv) do (
  if not exist "%FILES_DIR%\%%F" (
    echo [FAIL] Missing prospective input: %%F
    >"%OUTPUT_DIR%\FRESH_PROSPECTIVE_RUN_ERROR.txt" echo Missing %FILES_DIR%\%%F
    exit /b 4
  )
)

if not exist "%CONFIG_PATH%" (
  echo [FAIL] Frozen fresh-prospective config is missing.
  >"%OUTPUT_DIR%\FRESH_PROSPECTIVE_RUN_ERROR.txt" echo Missing %CONFIG_PATH%
  exit /b 4
)

echo ============================================================
echo GOLD_ML_V1 - FRESH PROSPECTIVE CONFIRMATION AUDIT ONLY
echo Cutoff: strictly after 2026-06-23 18:15:00 MT5 server close
echo Frozen nine candidates / closed goldsharp bars only
echo ============================================================

%PYTHON_CMD% scripts\gold_ml_v1\prospective\run_fresh_prospective_confirmation.py ^
  --files-dir "%FILES_DIR%" ^
  --config "%CONFIG_PATH%" ^
  --output-dir "%OUTPUT_DIR%"
set "RC=%ERRORLEVEL%"

if "%RC%"=="0" (
  echo [PASS] Fresh prospective report completed. No automatic next phase was started.
) else (
  echo [FAIL] Fresh prospective validation or report generation failed. Exit code: %RC%
  echo Check %OUTPUT_DIR%\LATEST_RUN_SUMMARY.txt and FRESH_PROSPECTIVE_RUN_ERROR.txt
)

exit /b %RC%
