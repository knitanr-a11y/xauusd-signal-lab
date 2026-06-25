@echo off
setlocal
cd /d "%~dp0\..\..\.."
if "%~1"=="" (
  echo Usage: %~nx0 ^<GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip^>
  exit /b 1
)
py -3.12 scripts\gold_ml_v1\tools\install_batch023_local_replay_artifacts.py "%~1" --repo-root "%CD%"
set RC=%ERRORLEVEL%
echo.
echo Exit code: %RC%
pause
exit /b %RC%
