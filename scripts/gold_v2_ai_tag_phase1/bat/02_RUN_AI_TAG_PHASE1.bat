@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM This BAT is stored in:
REM   Files\xauusd-signal-lab-clean\xauusd-signal-lab\scripts\gold_v2_ai_tag_phase1\bat
REM It writes outputs to:
REM   Files\FX_OUTPUTS\gold_v2_ai_tag_phase1
REM It reads existing env from:
REM   Files\xauusd-signal-lab\.env

set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
for %%I in ("%REPO_ROOT%\..\..") do set "FILES_DIR=%%~fI"

set "OUTPUT_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v2_ai_tag_phase1"
set "ENV_FILE=%FILES_DIR%\xauusd-signal-lab\.env"
set "RUNNER=%REPO_ROOT%\scripts\gold_v2_ai_tag_phase1\run_gold_v2_ai_tag_phase1_with_progress.py"

set "INPUT=%OUTPUT_DIR%\gold_v2_ai_phase1_input_snapshots.csv"
set "SCHEMA=%OUTPUT_DIR%\gold_v2_ai_tag_schema.json"
set "OUTPUT=%OUTPUT_DIR%\gold_v2_ai_phase1_ai_tags.csv"
set "LOG_DIR=%OUTPUT_DIR%\logs"
set "LOG_FILE=%LOG_DIR%\gold_v2_ai_phase1_run.log"

REM Change model here if needed.
set "MODEL=gpt-5-mini"
set "TIMEOUT_SEC=8"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo [GOLD V2 AI TAG PHASE1] Start
echo REPO_ROOT=%REPO_ROOT%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo ENV_FILE=%ENV_FILE%
echo.

if not exist "%ENV_FILE%" (
  echo [ERROR] Existing .env not found: %ENV_FILE%
  echo Expected structure:
  echo   Files\xauusd-signal-lab\.env
  echo   Files\xauusd-signal-lab-clean\xauusd-signal-lab\...
  echo   Files\FX_OUTPUTS\gold_v2_ai_tag_phase1\...
  pause
  exit /b 1
)

if not exist "%INPUT%" (
  echo [ERROR] Input snapshot CSV not found: %INPUT%
  echo Put/extract the Phase 1 design files under Files\FX_OUTPUTS\gold_v2_ai_tag_phase1
  pause
  exit /b 1
)

if not exist "%SCHEMA%" (
  echo [ERROR] Schema JSON not found: %SCHEMA%
  echo Put/extract gold_v2_ai_tag_schema.json under Files\FX_OUTPUTS\gold_v2_ai_tag_phase1
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
echo [GOLD V2 AI TAG PHASE1] Finished with exit code %RC%
echo Output: %OUTPUT%
echo Log:    %LOG_FILE%

echo.
pause
exit /b %RC%
