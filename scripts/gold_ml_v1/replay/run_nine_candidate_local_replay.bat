@echo off
setlocal
cd /d "%~dp0\..\..\.."
if "%~1"=="" (
  echo Usage: %~nx0 ^<historical gold_v3_2023_2026 folder^>
  echo This historical exact replay intentionally ignores goldsharp files.
  exit /b 1
)
set "HISTORICAL_DIR=%~1"
py -3.12 -m pip install -r scripts\gold_ml_v1\replay\requirements-local-replay.txt
if errorlevel 1 exit /b 4
py -3.12 scripts\gold_ml_v1\replay\nine_candidate_local_replay.py --repo-root "%CD%" --mode raw --raw-dir "%HISTORICAL_DIR%" --output-dir outputs\gold_ml_v1\batch023_historical_replay
set RC=%ERRORLEVEL%
echo.
echo Exit code: %RC%
pause
exit /b %RC%
