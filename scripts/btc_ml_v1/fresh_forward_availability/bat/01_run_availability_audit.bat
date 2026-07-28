@echo off
setlocal EnableExtensions DisableDelayedExpansion

REM BTC ML V1 Stage 01 fresh-forward availability audit-only.
REM User-facing BAT location:
REM scripts\btc_ml_v1\fresh_forward_availability\bat\01_run_availability_audit.bat

set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if defined LOCALAPPDATA (
  set "OUTPUT_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability"
) else (
  set "OUTPUT_ROOT=%TEMP%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability"
)
set "LATEST_DIR=%OUTPUT_ROOT%\LATEST"
set "UPLOAD_PACKAGE=%LATEST_DIR%\99_UPLOAD_PACKAGE.zip"
set "RUN_LOG=%OUTPUT_ROOT%\last_run_console.log"

if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"
if not exist "%OUTPUT_ROOT%" (
  echo [BTC_ML_V1_01] ERROR: output root could not be created.
  echo [BTC_ML_V1_01] Expected: %OUTPUT_ROOT%
  echo.
  pause
  exit /b 2
)

> "%RUN_LOG%" echo [BTC_ML_V1_01] fresh-forward availability read-only audit
>> "%RUN_LOG%" echo [BTC_ML_V1_01] launcher_contract=v3_nonempty_outputs_persistent_console_select_zip
>> "%RUN_LOG%" echo [BTC_ML_V1_01] repo_root=%REPO_ROOT%
>> "%RUN_LOG%" echo [BTC_ML_V1_01] output_root=%OUTPUT_ROOT%
>> "%RUN_LOG%" echo [BTC_ML_V1_01] external actions remain OFF: candidate_engine=false evaluator=false collector=false Discord=false MT5=false live_ready=false final_signal=false
>> "%RUN_LOG%" echo.

type "%RUN_LOG%"
echo.

python scripts\btc_ml_v1\fresh_forward_availability\python\audit_btc_fresh_forward_availability.py --output-root "%OUTPUT_ROOT%" %* >> "%RUN_LOG%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

type "%RUN_LOG%"
echo.
echo [BTC_ML_V1_01] exit_code=%EXIT_CODE%
echo [BTC_ML_V1_01] latest=%LATEST_DIR%
echo [BTC_ML_V1_01] persistent_log=%RUN_LOG%

if not "%EXIT_CODE%"=="0" goto :AUDIT_FAILED

if not exist "%LATEST_DIR%" goto :OUTPUT_INVALID

for %%F in (
  "%LATEST_DIR%\00_READ_ME_FIRST.txt"
  "%LATEST_DIR%\01_availability_summary.json"
  "%LATEST_DIR%\02_availability_report.txt"
  "%UPLOAD_PACKAGE%"
) do (
  if not exist "%%~fF" goto :OUTPUT_INVALID
  if %%~zF LEQ 0 goto :OUTPUT_INVALID
)

python -c "import json,sys,zipfile; from pathlib import Path; d=Path(sys.argv[1]); json.load((d/'01_availability_summary.json').open(encoding='utf-8')); z=zipfile.ZipFile(d/'99_UPLOAD_PACKAGE.zip'); names=set(z.namelist()); required={'00_READ_ME_FIRST.txt','01_availability_summary.json','02_availability_report.txt'}; assert required.issubset(names), f'missing ZIP entries: {sorted(required-names)}'; assert z.testzip() is None, 'corrupt ZIP entry'; z.close()" "%LATEST_DIR%" >> "%RUN_LOG%" 2>&1
set "VERIFY_EXIT_CODE=%ERRORLEVEL%"
if not "%VERIFY_EXIT_CODE%"=="0" goto :OUTPUT_INVALID

>> "%RUN_LOG%" echo.
>> "%RUN_LOG%" echo [BTC_ML_V1_01] Verified LATEST file listing:
dir /a-d "%LATEST_DIR%" >> "%RUN_LOG%" 2>&1

echo.
echo [BTC_ML_V1_01] SUCCESS: availability audit complete and all four output files were verified.
echo [BTC_ML_V1_01] Verified files on disk:
dir /a-d "%LATEST_DIR%"
echo.
echo [BTC_ML_V1_01] Explorer will open with 99_UPLOAD_PACKAGE.zip selected.
echo [BTC_ML_V1_01] Upload that single ZIP to ChatGPT.
echo [BTC_ML_V1_01] Fresh performance evaluation was not run.
echo [BTC_ML_V1_01] This command window will remain open until you press a key.
timeout /t 1 /nobreak >nul
start "" explorer.exe /select,"%UPLOAD_PACKAGE%"
echo.
pause
exit /b 0

:AUDIT_FAILED
echo.
echo [BTC_ML_V1_01] BLOCKED or FAILED. No result folder will be opened.
echo [BTC_ML_V1_01] Read the error above or open this persistent log:
echo [BTC_ML_V1_01] %RUN_LOG%
echo [BTC_ML_V1_01] This window will remain open.
echo.
pause
exit /b %EXIT_CODE%

:OUTPUT_INVALID
>> "%RUN_LOG%" echo [BTC_ML_V1_01] ERROR: Python returned success or LATEST existed, but the required non-empty outputs or ZIP validation failed.
echo.
echo [BTC_ML_V1_01] ERROR: LATEST is missing, empty, incomplete, or contains an invalid ZIP.
echo [BTC_ML_V1_01] The empty or incomplete folder will NOT be opened as success.
echo [BTC_ML_V1_01] Expected non-empty files:
echo [BTC_ML_V1_01]   %LATEST_DIR%\00_READ_ME_FIRST.txt
echo [BTC_ML_V1_01]   %LATEST_DIR%\01_availability_summary.json
echo [BTC_ML_V1_01]   %LATEST_DIR%\02_availability_report.txt
echo [BTC_ML_V1_01]   %UPLOAD_PACKAGE%
echo [BTC_ML_V1_01] Persistent log:
echo [BTC_ML_V1_01]   %RUN_LOG%
echo [BTC_ML_V1_01] This window will remain open.
echo.
pause
exit /b 3
