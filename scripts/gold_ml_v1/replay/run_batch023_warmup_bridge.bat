@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\.."

if "%~1"=="" goto :usage

set "RAW_DIR=%~1"
set "ZIP_PATH=%~2"
set "VENV_DIR=%CD%\.venv_batch023_bridge"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "OUTPUT_DIR=%CD%\outputs\gold_ml_v1\batch023_warmup_bridge_local"

if not exist "%RAW_DIR%" (
  echo [ERROR] Raw folder not found: %RAW_DIR%
  exit /b 1
)

if "%ZIP_PATH%"=="" (
  set "ZIP_PATH=%USERPROFILE%\Downloads\GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip"
  if not exist "%ZIP_PATH%" set "ZIP_PATH=%USERPROFILE%\Desktop\GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip"
)
if not exist "%ZIP_PATH%" (
  echo [ERROR] Batch023 ZIP not found.
  echo Pass it as the second argument, or place it in Downloads/Desktop.
  exit /b 1
)

if not exist "%PYTHON_EXE%" (
  echo ============================================================
  echo Creating isolated Python environment: .venv_batch023_bridge
  echo ============================================================
  py -3.12 -m venv "%VENV_DIR%"
  if errorlevel 1 exit /b 4
)

"%PYTHON_EXE%" -m pip install --disable-pip-version-check -r scripts\gold_ml_v1\replay\requirements-batch023-warmup-bridge.txt
if errorlevel 1 exit /b 4

echo ============================================================
echo GOLD_ML_V1 Batch023 Local Warmup Bridge

echo ============================================================
echo Raw folder : %RAW_DIR%
echo Batch023 ZIP: %ZIP_PATH%
echo Output     : %OUTPUT_DIR%
echo Audit only : YES

echo.

"%PYTHON_EXE%" scripts\gold_ml_v1\replay\run_batch023_warmup_bridge_local.py --raw-dir "%RAW_DIR%" --zip "%ZIP_PATH%" --output-dir "%OUTPUT_DIR%"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo [PASS] 9/9 candidate warmup-bridge parity passed.
  echo Summary: %OUTPUT_DIR%\LATEST_RUN_SUMMARY.txt
) else (
  echo [FAIL] Exit code: %RC%
  echo Error: %OUTPUT_DIR%\LOCAL_RUN_ERROR.txt
  echo Summary: %OUTPUT_DIR%\LATEST_RUN_SUMMARY.txt
)

echo.
echo WARMUP_BRIDGE_EXACT rows are historical audit rows only.
echo They must never emit live signals.
pause
exit /b %RC%

:usage
echo Usage:
echo   %~nx0 ^<gold_v3_2023_2026 folder^> [Batch023 ZIP path]
echo.
echo Example:
echo   %~nx0 "C:\path\to\gold_v3_2023_2026" "C:\Users\regen\Downloads\GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip"
exit /b 1
