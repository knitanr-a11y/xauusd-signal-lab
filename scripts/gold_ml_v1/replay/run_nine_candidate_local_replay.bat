@echo off
setlocal
cd /d "%~dp0\..\..\.."
if "%~1"=="" goto :usage
if "%~2"=="" goto :usage
set "HISTORICAL_DIR=%~1"
set "WARMUP_DIR=%~2"
py -3.12 -m pip install -r scripts\gold_ml_v1\replay\requirements-local-replay.txt
if errorlevel 1 exit /b 4
py -3.12 scripts\gold_ml_v1\replay\nine_candidate_local_replay_v2.py --repo-root "%CD%" --mode raw --historical-dir "%HISTORICAL_DIR%" --warmup-dir "%WARMUP_DIR%" --output-dir outputs\gold_ml_v1\batch023_historical_replay_v2
set RC=%ERRORLEVEL%
echo.
echo Exit code: %RC%
pause
exit /b %RC%

:usage
echo Usage: %~nx0 ^<historical gold_v3_2023_2026 folder^> ^<MQL5 Files folder containing goldsharp files^>
echo Historical rows are the only decision/trade window.
echo Older goldsharp rows are used only for indicator warmup.
exit /b 1
