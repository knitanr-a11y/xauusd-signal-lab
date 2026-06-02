@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
for %%I in ("%REPO_ROOT%\..\..") do set "FILES_DIR=%%~fI"

set "PHASE2_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v2_ai_tag_phase2"
set "ENV_FILE=%FILES_DIR%\xauusd-signal-lab\.env"
set "INPUT=%PHASE2_DIR%\gold_v2_ai_phase2_input_snapshots.csv"
set "SCHEMA=%PHASE2_DIR%\gold_v2_ai_tag_schema_v2.json"
set "OUTPUT=%PHASE2_DIR%\gold_v2_ai_phase2_ai_tags.csv"
set "RUNNER=%PHASE2_DIR%\run_gold_v2_ai_tag_phase2.py"
set "LOG_DIR=%PHASE2_DIR%\logs"
set "LOG_FILE=%LOG_DIR%\gold_v2_ai_phase2_run.log"
set "MODEL=gpt-4.1-mini"
set "TIMEOUT_SEC=12"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo [GOLD V2 AI TAG PHASE2] Start
echo PHASE2_DIR=%PHASE2_DIR%
echo ENV_FILE=%ENV_FILE%
echo MODEL=%MODEL%
echo OUTPUT=%OUTPUT%
echo.

if not exist "%ENV_FILE%" (
  echo [ERROR] env file not found: %ENV_FILE%
  pause
  exit /b 1
)
if not exist "%INPUT%" (
  echo [ERROR] input not found: %INPUT%
  pause
  exit /b 1
)
if not exist "%SCHEMA%" (
  echo [ERROR] schema not found: %SCHEMA%
  pause
  exit /b 1
)
if not exist "%RUNNER%" (
  echo [ERROR] runner not found: %RUNNER%
  pause
  exit /b 1
)

python "%RUNNER%" ^
  --input "%INPUT%" ^
  --schema "%SCHEMA%" ^
  --output "%OUTPUT%" ^
  --env-file "%ENV_FILE%" ^
  --model "%MODEL%" ^
  --timeout-sec %TIMEOUT_SEC% ^
  --sleep-sec 0.2 ^
  --resume ^
  --log-file "%LOG_FILE%"

set "RC=%ERRORLEVEL%"
echo.
echo [GOLD V2 AI TAG PHASE2] Finished with exit code %RC%
echo Output: %OUTPUT%
echo Log:    %LOG_FILE%
pause
exit /b %RC%
