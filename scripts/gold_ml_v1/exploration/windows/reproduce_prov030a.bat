@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\..\.."

set "RAW_DIR=%~1"
set "CONTRACT=%~2"
set "OUTPUT_DIR=outputs\gold_ml_v1\prov030a_local_reproduction"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

set "PYTHON_CMD="
if exist ".venv_batch023_bridge\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023_bridge\Scripts\python.exe"
if not defined PYTHON_CMD if exist ".venv_batch023\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023\Scripts\python.exe"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  >"%OUTPUT_DIR%\LOCAL_REPRODUCTION_ERROR.txt" echo status=FAIL
  >>"%OUTPUT_DIR%\LOCAL_REPRODUCTION_ERROR.txt" echo error=Python 3.12 could not be found.
  exit /b 4
)
if "%RAW_DIR%"=="" exit /b 4
if "%CONTRACT%"=="" set "CONTRACT=config\gold_ml_v1\provisional_candidate_gml1_prov_030_a_20260625.json"

for %%F in (gold_v3_2023_2026_m1.csv gold_v3_2023_2026_m5.csv gold_v3_2023_2026_m15.csv gold_v3_2023_2026_h1.csv gold_v3_2023_2026_h4.csv gold_v3_2023_2026_d1.csv) do (
  if not exist "%RAW_DIR%\%%F" (
    >"%OUTPUT_DIR%\LOCAL_REPRODUCTION_ERROR.txt" echo status=FAIL
    >>"%OUTPUT_DIR%\LOCAL_REPRODUCTION_ERROR.txt" echo error=Missing %RAW_DIR%\%%F
    exit /b 4
  )
)
if not exist "%CONTRACT%" exit /b 4

echo ============================================================
echo GOLD_ML_V1 - GML1-PROV-030-A LOCAL AUDIT REPRODUCTION
echo time column is MT5 server bar-open time
echo provisional research-only candidate; no live activation
echo ============================================================

%PYTHON_CMD% scripts\gold_ml_v1\exploration\run_prov030a_local_reproduction.py ^
  --raw-dir "%RAW_DIR%" ^
  --contract "%CONTRACT%" ^
  --output-dir "%OUTPUT_DIR%"
exit /b %ERRORLEVEL%
