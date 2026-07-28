@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

if defined LOCALAPPDATA (
  set "OUTPUT_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W24B"
) else (
  set "OUTPUT_ROOT=%TEMP%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W24B"
)
set "LATEST=%OUTPUT_ROOT%\LATEST"
set "PACKAGE=%LATEST%\99_UPLOAD_PACKAGE.zip"
set "RUN_LOG=%OUTPUT_ROOT%\last_run_console.log"

if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"
if not exist "%OUTPUT_ROOT%" (
  echo [M10W24B ERROR] Output root could not be created.
  echo Expected: %OUTPUT_ROOT%
  echo.
  pause
  exit /b 2
)

> "%RUN_LOG%" echo [M10W24B] NEITHER cohort scope correction audit-only
>> "%RUN_LOG%" echo [M10W24B] operator_contract=v2_verify_outputs_keep_console_select_zip
>> "%RUN_LOG%" echo [M10W24B] repo_root=%CD%
>> "%RUN_LOG%" echo [M10W24B] output_root=%OUTPUT_ROOT%
>> "%RUN_LOG%" echo [M10W24B] existing monitors and frozen starts remain unchanged
>> "%RUN_LOG%" echo.

type "%RUN_LOG%"
echo.

python "scripts\mochipoyo_alert_research\m10w24b\python\run_m10w24b_neither_cohort_scope_correction.py" >> "%RUN_LOG%" 2>&1
set "RC=%ERRORLEVEL%"

type "%RUN_LOG%"
echo.
echo [M10W24B] exit_code=%RC%
echo [M10W24B] latest=%LATEST%
echo [M10W24B] persistent_log=%RUN_LOG%

if not "%RC%"=="0" goto :BLOCKED
if not exist "%LATEST%" goto :OUTPUT_INVALID

for %%F in (
  "%LATEST%\00_READ_ME_FIRST.txt"
  "%LATEST%\01_summary.json"
  "%LATEST%\02_corrected_neither_feature_rows.csv"
  "%LATEST%\03_trade_ledger_all_families.csv"
  "%LATEST%\04_overlap_skip_ledger_all_families.csv"
  "%LATEST%\05_audit.log"
  "%PACKAGE%"
) do (
  if not exist "%%~fF" goto :OUTPUT_INVALID
)

for %%F in (
  "%LATEST%\00_READ_ME_FIRST.txt"
  "%LATEST%\01_summary.json"
  "%LATEST%\02_corrected_neither_feature_rows.csv"
  "%LATEST%\03_trade_ledger_all_families.csv"
  "%LATEST%\05_audit.log"
  "%PACKAGE%"
) do (
  if %%~zF LEQ 0 goto :OUTPUT_INVALID
)

python -c "import json,sys,zipfile; from pathlib import Path; d=Path(sys.argv[1]); json.load((d/'01_summary.json').open(encoding='utf-8')); z=zipfile.ZipFile(d/'99_UPLOAD_PACKAGE.zip'); names=set(z.namelist()); required={'00_READ_ME_FIRST.txt','01_summary.json','02_corrected_neither_feature_rows.csv','03_trade_ledger_all_families.csv','04_overlap_skip_ledger_all_families.csv','05_audit.log'}; assert required.issubset(names), f'missing ZIP entries: {sorted(required-names)}'; assert z.testzip() is None, 'corrupt ZIP entry'; z.close()" "%LATEST%" >> "%RUN_LOG%" 2>&1
set "VERIFY_RC=%ERRORLEVEL%"
if not "%VERIFY_RC%"=="0" goto :OUTPUT_INVALID

>> "%RUN_LOG%" echo.
>> "%RUN_LOG%" echo [M10W24B] Verified LATEST file listing:
dir /a-d "%LATEST%" >> "%RUN_LOG%" 2>&1

echo.
echo [M10W24B COMPLETE]
echo All required output files and the upload ZIP were verified.
echo Verified files on disk:
dir /a-d "%LATEST%"
echo.
echo Explorer will open with 99_UPLOAD_PACKAGE.zip selected.
echo Upload only that ZIP.
echo This command window will remain open until you press a key.
timeout /t 1 /nobreak >nul
start "" explorer.exe /select,"%PACKAGE%"
echo.
pause
exit /b 0

:BLOCKED
echo.
echo [STOP] M10W24B was BLOCKED. Do not alter the frozen cohort correction or hypotheses.
echo Read the error above or open this persistent log:
echo %RUN_LOG%
echo This window will remain open.
echo.
pause
exit /b %RC%

:OUTPUT_INVALID
>> "%RUN_LOG%" echo [M10W24B ERROR] Required outputs were missing, empty where non-empty was required, or ZIP/JSON validation failed.
echo.
echo [M10W24B ERROR] Python returned success or LATEST existed, but the submission package is incomplete or invalid.
echo Explorer will NOT be opened as success.
echo Persistent log:
echo %RUN_LOG%
echo This window will remain open.
echo.
pause
exit /b 3
