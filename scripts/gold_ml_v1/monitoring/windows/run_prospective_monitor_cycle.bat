@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\..\.."

set "FILES_DIR=%~1"
set "CONFIG_PATH=%~2"
set "OUTPUT_DIR=outputs\gold_ml_v1\prospective_monitoring"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

if "%FILES_DIR%"=="" (
  echo [FAIL] MQL5 Files directory was not supplied.
  >"%OUTPUT_DIR%\MONITOR_RUN_ERROR.txt" echo Missing MQL5 Files directory argument.
  exit /b 4
)
if "%CONFIG_PATH%"=="" set "CONFIG_PATH=config\gold_ml_v1\prospective_monitoring_20260625.json"

set "PYTHON_CMD="
if exist ".venv_batch023_bridge\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023_bridge\Scripts\python.exe"
if not defined PYTHON_CMD if exist ".venv_batch023\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023\Scripts\python.exe"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  echo [FAIL] Python 3.12 could not be found.
  >"%OUTPUT_DIR%\MONITOR_RUN_ERROR.txt" echo Python 3.12 could not be found.
  exit /b 4
)

for %%F in (goldsharp_m1.csv goldsharp_m15.csv goldsharp_h1.csv goldsharp_h4.csv goldsharp_d1.csv) do (
  if not exist "%FILES_DIR%\%%F" (
    echo [FAIL] Missing monitoring input: %%F
    >"%OUTPUT_DIR%\MONITOR_RUN_ERROR.txt" echo Missing %FILES_DIR%\%%F
    exit /b 4
  )
)

if not exist "%CONFIG_PATH%" (
  echo [FAIL] Frozen monitoring config is missing.
  >"%OUTPUT_DIR%\MONITOR_RUN_ERROR.txt" echo Missing %CONFIG_PATH%
  exit /b 4
)

echo ============================================================
echo GOLD_ML_V1 - STATEFUL PROSPECTIVE MONITOR AUDIT ONLY
echo Frozen nine candidates / closed goldsharp bars only
echo One monitoring cycle; no background task, notification or order
echo ============================================================

%PYTHON_CMD% scripts\gold_ml_v1\monitoring\run_prospective_monitor_cycle.py ^
  --files-dir "%FILES_DIR%" ^
  --config "%CONFIG_PATH%" ^
  --output-dir "%OUTPUT_DIR%"
set "RC=%ERRORLEVEL%"

if "%RC%"=="0" (
  echo [PASS] Stateful prospective monitoring cycle completed.
) else (
  echo [FAIL] Monitoring validation or ledger update failed. Exit code: %RC%
  echo Check %OUTPUT_DIR%\LATEST_RUN_SUMMARY.txt and MONITOR_RUN_ERROR.txt
)

exit /b %RC%
