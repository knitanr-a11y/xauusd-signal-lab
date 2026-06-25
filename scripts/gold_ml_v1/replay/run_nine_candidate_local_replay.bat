@echo off
setlocal
cd /d "%~dp0\..\..\.."
if "%~1"=="" goto :usage
if "%~2"=="" goto :usage
set "HISTORICAL_DIR=%~1"
set "WARMUP_DIR=%~2"
set "VENV_DIR=%CD%\.venv_batch023"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  py -3.12 -m venv "%VENV_DIR%"
  if errorlevel 1 exit /b 4
)
"%PYTHON_EXE%" -m pip install -r scripts\gold_ml_v1\replay\requirements-local-replay.txt
if errorlevel 1 exit /b 4
"%PYTHON_EXE%" scripts\gold_ml_v1\replay\nine_candidate_local_replay_v3.py --repo-root "%CD%" --mode raw --historical-dir "%HISTORICAL_DIR%" --warmup-dir "%WARMUP_DIR%" --output-dir outputs\gold_ml_v1\batch023_historical_replay_v3
set RC=%ERRORLEVEL%
echo.
echo Exit code: %RC%
pause
exit /b %RC%

:usage
echo Usage: %~nx0 ^<historical gold_v3_2023_2026 folder^> ^<MQL5 Files folder containing goldsharp files^>
echo Historical rows are the only decision/trade window.
echo Older goldsharp rows are used only for indicator warmup.
echo Weekend and maintenance gaps use the last available M1 close within the horizon.
exit /b 1
