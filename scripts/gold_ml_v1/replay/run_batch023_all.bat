@echo off
setlocal
cd /d "%~dp0\..\..\.."

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage
if "%~3"=="" goto :usage

set "ARTIFACT_ZIP=%~1"
set "HISTORICAL_DIR=%~2"
set "LIVE_DIR=%~3"
set "VENV_DIR=%CD%\.venv_batch023"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if not exist "%ARTIFACT_ZIP%" exit /b 1
if not exist "%HISTORICAL_DIR%" exit /b 1
if not exist "%LIVE_DIR%" exit /b 1

if not exist "%PYTHON_EXE%" (
  py -3.12 -m venv "%VENV_DIR%"
  if errorlevel 1 exit /b 4
)

"%PYTHON_EXE%" -m pip install -r scripts\gold_ml_v1\replay\requirements-local-replay.txt
if errorlevel 1 exit /b 4

echo ============================================================
echo STEP 1/4 Install verified exact registries
echo ============================================================
"%PYTHON_EXE%" scripts\gold_ml_v1\tools\install_batch023_local_replay_artifacts.py "%ARTIFACT_ZIP%" --repo-root "%CD%"
if errorlevel 1 goto :failed

echo ============================================================
echo STEP 2/4 Verify expected registries
echo ============================================================
"%PYTHON_EXE%" scripts\gold_ml_v1\replay\nine_candidate_local_replay.py --repo-root "%CD%" --mode registry-only --output-dir outputs\gold_ml_v1\batch023_registry_parity
if errorlevel 1 goto :failed

echo ============================================================
echo STEP 3/4 Historical replay V5
echo   ATR14: frozen Wilder SMA-seed
echo   raw time: bar-open time
echo   M15 onset: false-to-true on state AND eligibility
echo   H1 event: frozen Batch006 event-before-execution order
echo ============================================================
"%PYTHON_EXE%" scripts\gold_ml_v1\replay\replay_v5_entry.py --repo-root "%CD%" --historical-dir "%HISTORICAL_DIR%" --warmup-dir "%LIVE_DIR%" --output-dir outputs\gold_ml_v1\batch023_historical_replay_v5
if errorlevel 1 goto :failed

echo ============================================================
echo STEP 4/4 Goldsharp source preflight
echo ============================================================
"%PYTHON_EXE%" scripts\gold_ml_v1\replay\goldsharp_live_source_preflight.py --historical-dir "%HISTORICAL_DIR%" --live-dir "%LIVE_DIR%" --output-dir outputs\gold_ml_v1\goldsharp_live_source_preflight
if errorlevel 1 goto :failed

echo [PASS] Batch023 completed.
pause
exit /b 0

:usage
echo Usage: %~nx0 ZIP HISTORICAL_DIR LIVE_DIR
exit /b 1

:failed
set RC=%ERRORLEVEL%
echo [FAIL] Exit code: %RC%
echo Check outputs\gold_ml_v1\batch023_historical_replay_v5
pause
exit /b %RC%
