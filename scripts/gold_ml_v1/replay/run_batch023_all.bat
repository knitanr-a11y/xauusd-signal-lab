@echo off
setlocal
cd /d "%~dp0\..\..\.."

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage
if "%~3"=="" goto :usage

set "ARTIFACT_ZIP=%~1"
set "HISTORICAL_DIR=%~2"
set "LIVE_DIR=%~3"

if not exist "%ARTIFACT_ZIP%" (
  echo [ERROR] ZIP not found: %ARTIFACT_ZIP%
  exit /b 1
)
if not exist "%HISTORICAL_DIR%" (
  echo [ERROR] Historical folder not found: %HISTORICAL_DIR%
  exit /b 1
)
if not exist "%LIVE_DIR%" (
  echo [ERROR] Live folder not found: %LIVE_DIR%
  exit /b 1
)

echo ============================================================
echo STEP 1/4 Install verified exact registries from Batch023 ZIP
echo ============================================================
py -3.12 scripts\gold_ml_v1\tools\install_batch023_local_replay_artifacts.py "%ARTIFACT_ZIP%" --repo-root "%CD%"
if errorlevel 1 goto :failed

echo ============================================================
echo STEP 2/4 Verify 9 expected registries and parent derivations
echo ============================================================
py -3.12 -m pip install -r scripts\gold_ml_v1\replay\requirements-local-replay.txt
if errorlevel 1 exit /b 4
py -3.12 scripts\gold_ml_v1\replay\nine_candidate_local_replay.py --repo-root "%CD%" --mode registry-only --output-dir outputs\gold_ml_v1\batch023_registry_parity
if errorlevel 1 goto :failed

echo ============================================================
echo STEP 3/4 Historical exact replay using gold_v3_2023_2026 only
echo ============================================================
py -3.12 scripts\gold_ml_v1\replay\nine_candidate_local_replay.py --repo-root "%CD%" --mode raw --raw-dir "%HISTORICAL_DIR%" --output-dir outputs\gold_ml_v1\batch023_historical_replay
if errorlevel 1 goto :failed

echo ============================================================
echo STEP 4/4 Audit goldsharp as the live-only new-bar source
echo ============================================================
py -3.12 scripts\gold_ml_v1\replay\goldsharp_live_source_preflight.py --historical-dir "%HISTORICAL_DIR%" --live-dir "%LIVE_DIR%" --output-dir outputs\gold_ml_v1\goldsharp_live_source_preflight
if errorlevel 1 goto :failed

echo.
echo [PASS] Batch023 completed.
echo Historical replay used only gold_v3_2023_2026 files.
echo Live preflight treated only goldsharp rows after the historical maximum as new operational rows.
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
echo Check outputs\gold_ml_v1 for the generated report.
pause
exit /b %RC%
