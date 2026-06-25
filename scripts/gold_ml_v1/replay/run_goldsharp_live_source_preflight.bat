@echo off
setlocal
cd /d "%~dp0\..\..\.."
if "%~1"=="" (
  echo Usage: %~nx0 ^<historical gold_v3_2023_2026 folder^> ^<MQL5 Files folder containing goldsharp_*.csv^>
  exit /b 1
)
if "%~2"=="" (
  echo Usage: %~nx0 ^<historical gold_v3_2023_2026 folder^> ^<MQL5 Files folder containing goldsharp_*.csv^>
  exit /b 1
)
set "HISTORICAL_DIR=%~1"
set "LIVE_DIR=%~2"
py -3.12 -m pip install -r scripts\gold_ml_v1\replay\requirements-local-replay.txt
if errorlevel 1 exit /b 4
py -3.12 scripts\gold_ml_v1\replay\goldsharp_live_source_preflight.py --historical-dir "%HISTORICAL_DIR%" --live-dir "%LIVE_DIR%" --output-dir outputs\gold_ml_v1\goldsharp_live_source_preflight
set RC=%ERRORLEVEL%
echo.
echo Exit code: %RC%
pause
exit /b %RC%
