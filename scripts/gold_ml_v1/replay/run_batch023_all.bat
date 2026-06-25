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

if not exist "%ARTIFACT_ZIP%" (
  echo [ERROR] ZIP not found: %ARTIFACT_ZIP%
  exit /b 1
)
if not exist "%HISTORICAL_DIR%" (
  echo [ERROR] Historical folder not found: %HISTORICAL_DIR%
  exit /b 1
)
if not exist "%LIVE_DIR%" (
  echo [ERROR] Live/warmup folder not found: %LIVE_DIR%
  exit /b 1
)

if not exist "%PYTHON_EXE%" (
  echo ============================================================
  echo SETUP Create isolated Python environment .venv_batch023
  echo ============================================================
  py -3.12 -m venv "%VENV_DIR%"
  if errorlevel 1 exit /b 4
)

"%PYTHON_EXE%" -m pip install -r scripts\gold_ml_v1\replay\requirements-local-replay.txt
if errorlevel 1 exit /b 4

echo ============================================================
echo STEP 1/4 Install verified exact registries from Batch023 ZIP
echo ============================================================
"%PYTHON_EXE%" scripts\gold_ml_v1\tools\install_batch023_local_replay_artifacts.py "%ARTIFACT_ZIP%" --repo-root "%CD%"
if errorlevel 1 goto :failed

echo ============================================================
echo STEP 2/4 Verify 9 expected registries and parent derivations
echo ============================================================
"%PYTHON_EXE%" scripts\gold_ml_v1\replay\nine_candidate_local_replay.py --repo-root "%CD%" --mode registry-only --output-dir outputs\gold_ml_v1\batch023_registry_parity
if errorlevel 1 goto :failed

echo ============================================================
echo STEP 3/4 Exact-contract historical replay V4
echo   raw time is fixed as bar-open time
echo   stored H4/M15 features must reproduce exactly
echo   RCI implementation is selected only if all M15 candidates match
echo   H1 event order is restored to the frozen Batch006 evaluator
echo ============================================================
"%PYTHON_EXE%" scripts\gold_ml_v1\replay\nine_candidate_local_replay_v4.py --repo-root "%CD%" --historical-dir "%HISTORICAL_DIR%" --warmup-dir "%LIVE_DIR%" --output-dir outputs\gold_ml_v1\batch023_historical_replay_v4
if errorlevel 1 goto :failed

echo ============================================================
echo STEP 4/4 Audit goldsharp as the live-only new-bar source
echo ============================================================
"%PYTHON_EXE%" scripts\gold_ml_v1\replay\goldsharp_live_source_preflight.py --historical-dir "%HISTORICAL_DIR%" --live-dir "%LIVE_DIR%" --output-dir outputs\gold_ml_v1\goldsharp_live_source_preflight
if errorlevel 1 goto :failed

echo.
echo [PASS] Batch023 completed.
echo Historical decisions used only gold_v3_2023_2026 rows.
echo Stored feature values and all nine exact registries matched.
echo Goldsharp was audited as the live-only new-bar source.
echo Python packages were installed only inside .venv_batch023.
pause
exit /b 0

:usage
echo Usage:
echo %~nx0 ^<Batch023 ZIP path^> ^<gold_v3_2023_2026 folder^> ^<MQL5 Files folder containing goldsharp files^>
echo.
echo The ZIP is only the verified answer-key registries. Do not extract it manually.
exit /b 1

:failed
set RC=%ERRORLEVEL%
echo.
echo [FAIL] Batch023 stopped at the first failed step. Exit code: %RC%
echo Check outputs\gold_ml_v1\batch023_historical_replay_v4 for the exact contract report.
pause
exit /b %RC%
