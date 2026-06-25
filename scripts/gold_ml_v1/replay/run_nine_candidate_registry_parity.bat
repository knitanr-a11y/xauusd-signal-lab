@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3.12 -m pip install -r scripts\gold_ml_v1\replay\requirements-local-replay.txt
if errorlevel 1 exit /b 4
py -3.12 scripts\gold_ml_v1\replay\nine_candidate_local_replay.py --repo-root "%CD%" --mode registry-only --output-dir outputs\gold_ml_v1\batch023_registry_parity
set RC=%ERRORLEVEL%
echo.
echo Exit code: %RC%
pause
exit /b %RC%
