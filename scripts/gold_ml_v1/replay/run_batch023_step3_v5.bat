@echo off
setlocal
cd /d "%~dp0\..\..\.."

if "%~1"=="" goto :usage

set "HISTORICAL_DIR=%~1"
set "PYTHON_EXE=%CD%\.venv_batch023\Scripts\python.exe"
set "ZIP_PATH=%USERPROFILE%\Downloads\GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip"

if not exist "%PYTHON_EXE%" (
  echo [ERROR] .venv_batch023 is missing. Run run_batch023_all.bat once.
  exit /b 4
)
if not exist "%HISTORICAL_DIR%" (
  echo [ERROR] Historical folder not found: %HISTORICAL_DIR%
  exit /b 1
)
if not exist "%ZIP_PATH%" (
  set "ZIP_PATH=%USERPROFILE%\Desktop\GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip"
)
if not exist "%ZIP_PATH%" (
  echo [ERROR] Verified Batch023 ZIP was not found in Downloads or Desktop.
  exit /b 1
)

echo ============================================================
echo Batch023 STEP 3 ONLY - FROZEN ORIGINAL EVALUATOR
echo ============================================================
echo Evaluator: replay_nine_candidates.py extracted from verified ZIP
echo Raw data : gold_v3_2023_2026 only
echo Goldsharp: not used in historical replay

"%PYTHON_EXE%" scripts\gold_ml_v1\replay\run_frozen_batch023_from_zip.py --zip "%ZIP_PATH%" --historical-dir "%HISTORICAL_DIR%" --output-dir outputs\gold_ml_v1\batch023_frozen_exact_replay
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" (
  echo [PASS] Batch023 frozen exact historical replay
) else (
  echo [FAIL] Exit code: %RC%
  echo Check outputs\gold_ml_v1\batch023_frozen_exact_replay
)
pause
exit /b %RC%

:usage
echo Usage: %~nx0 HISTORICAL_DIR [LIVE_DIR_IGNORED]
exit /b 1
