@echo off
setlocal
cd /d "%~dp0\..\..\.."

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage

set "HISTORICAL_DIR=%~1"
set "LIVE_DIR=%~2"
set "PYTHON_EXE=%CD%\.venv_batch023\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo [ERROR] .venv_batch023 is missing. Run run_batch023_all.bat once.
  exit /b 4
)
if not exist "%HISTORICAL_DIR%" exit /b 1
if not exist "%LIVE_DIR%" exit /b 1

echo ============================================================
echo Batch023 STEP 3 ONLY - Historical replay V5
echo ============================================================
"%PYTHON_EXE%" scripts\gold_ml_v1\replay\replay_v5_entry.py --repo-root "%CD%" --historical-dir "%HISTORICAL_DIR%" --warmup-dir "%LIVE_DIR%" --output-dir outputs\gold_ml_v1\batch023_historical_replay_v5
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" (
  echo [PASS] Batch023 historical replay V5
) else (
  echo [FAIL] Exit code: %RC%
  echo Check outputs\gold_ml_v1\batch023_historical_replay_v5
)
pause
exit /b %RC%

:usage
echo Usage: %~nx0 HISTORICAL_DIR LIVE_DIR
exit /b 1
