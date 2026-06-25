@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\..\.."

set "RAW_DIR=%~1"
set "CONFIG_PATH=%~2"
set "OUTPUT_DIR=outputs\gold_ml_v1\exploration_batch024_data_upload"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

if "%RAW_DIR%"=="" (
  echo [FAIL] Frozen raw history directory was not supplied.
  >"%OUTPUT_DIR%\PACKAGE_RUN_ERROR.txt" echo status=FAIL
  >>"%OUTPUT_DIR%\PACKAGE_RUN_ERROR.txt" echo error=Missing raw history directory argument.
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
  >"%OUTPUT_DIR%\PACKAGE_RUN_ERROR.txt" echo status=FAIL
  >>"%OUTPUT_DIR%\PACKAGE_RUN_ERROR.txt" echo error=Python 3.12 could not be found.
  exit /b 4
)

for %%F in (gold_v3_2023_2026_m1.csv gold_v3_2023_2026_m15.csv gold_v3_2023_2026_h1.csv) do (
  if not exist "%RAW_DIR%\%%F" (
    echo [FAIL] Missing frozen RAW input: %%F
    >"%OUTPUT_DIR%\PACKAGE_RUN_ERROR.txt" echo status=FAIL
    >>"%OUTPUT_DIR%\PACKAGE_RUN_ERROR.txt" echo error=Missing %RAW_DIR%\%%F
    exit /b 4
  )
)

if not exist "%CONFIG_PATH%" (
  echo [FAIL] Frozen Batch024 config is missing.
  >"%OUTPUT_DIR%\PACKAGE_RUN_ERROR.txt" echo status=FAIL
  >>"%OUTPUT_DIR%\PACKAGE_RUN_ERROR.txt" echo error=Missing %CONFIG_PATH%
  exit /b 4
)

echo ============================================================
echo GOLD_ML_V1 - PACKAGE FROZEN RAW INPUT FOR CHATGPT
echo This does NOT run exploration locally.
echo M1/M15/H1 hashes must exactly match the frozen records.
echo ============================================================

%PYTHON_CMD% scripts\gold_ml_v1\exploration\package_batch024_raw_for_assistant.py ^
  --raw-dir "%RAW_DIR%" ^
  --config "%CONFIG_PATH%" ^
  --output-dir "%OUTPUT_DIR%" ^
  --repo-root "%CD%"
set "RC=%ERRORLEVEL%"

if "%RC%"=="0" (
  echo [PASS] Frozen RAW archive created for upload to ChatGPT.
) else (
  echo [FAIL] RAW packaging failed. Exit code: %RC%
  echo Check %OUTPUT_DIR%\PACKAGE_RUN_ERROR.txt
)

exit /b %RC%
