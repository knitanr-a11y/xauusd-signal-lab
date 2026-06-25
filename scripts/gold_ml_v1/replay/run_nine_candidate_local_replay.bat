@echo off
setlocal
cd /d "%~dp0\..\..\.."
if "%~1"=="" (
  set "RAW_DIR=%CD%"
) else (
  set "RAW_DIR=%~1"
)
py -3.12 -m pip install -r scripts\gold_ml_v1\replay\requirements-local-replay.txt
if errorlevel 1 exit /b 4
py -3.12 scripts\gold_ml_v1\replay\nine_candidate_local_replay.py --repo-root "%CD%" --mode auto --raw-dir "%RAW_DIR%" --output-dir outputs\gold_ml_v1\batch023_local_replay
set RC=%ERRORLEVEL%
echo.
echo Exit code: %RC%
pause
exit /b %RC%
