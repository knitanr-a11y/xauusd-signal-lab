@echo off
setlocal EnableExtensions DisableDelayedExpansion

if defined LOCALAPPDATA (
  set "OUTPUT_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability"
) else (
  set "OUTPUT_ROOT=%TEMP%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability"
)
set "LATEST_DIR=%OUTPUT_ROOT%\LATEST"
set "RUN_LOG=%OUTPUT_ROOT%\last_run_console.log"

if not exist "%LATEST_DIR%" goto :INVALID_LATEST

for %%F in (
  "%LATEST_DIR%\00_READ_ME_FIRST.txt"
  "%LATEST_DIR%\01_availability_summary.json"
  "%LATEST_DIR%\02_availability_report.txt"
  "%LATEST_DIR%\99_UPLOAD_PACKAGE.zip"
) do (
  if not exist "%%~fF" goto :INVALID_LATEST
  if %%~zF LEQ 0 goto :INVALID_LATEST
)

python -c "import json,sys,zipfile; from pathlib import Path; d=Path(sys.argv[1]); json.load((d/'01_availability_summary.json').open(encoding='utf-8')); z=zipfile.ZipFile(d/'99_UPLOAD_PACKAGE.zip'); names=set(z.namelist()); required={'00_READ_ME_FIRST.txt','01_availability_summary.json','02_availability_report.txt'}; assert required.issubset(names), f'missing ZIP entries: {sorted(required-names)}'; assert z.testzip() is None, 'corrupt ZIP entry'; z.close()" "%LATEST_DIR%" >nul 2>&1
if errorlevel 1 goto :INVALID_LATEST

echo [BTC_ML_V1_01] Verified all four LATEST output files.
echo [BTC_ML_V1_01] Opened: %LATEST_DIR%
echo [BTC_ML_V1_01] This command window will remain open until you press a key.
start "" explorer.exe "%LATEST_DIR%"
echo.
pause
exit /b 0

:INVALID_LATEST
echo [BTC_ML_V1_01] ERROR: LATEST is missing, empty, incomplete, or contains an invalid ZIP.
echo [BTC_ML_V1_01] Run 01_run_availability_audit.bat again after pulling the latest commit.
echo [BTC_ML_V1_01] Expected non-empty files:
echo [BTC_ML_V1_01]   %LATEST_DIR%\00_READ_ME_FIRST.txt
echo [BTC_ML_V1_01]   %LATEST_DIR%\01_availability_summary.json
echo [BTC_ML_V1_01]   %LATEST_DIR%\02_availability_report.txt
echo [BTC_ML_V1_01]   %LATEST_DIR%\99_UPLOAD_PACKAGE.zip
echo [BTC_ML_V1_01] Persistent log, if present:
echo [BTC_ML_V1_01]   %RUN_LOG%
echo [BTC_ML_V1_01] This window will remain open.
echo.
pause
exit /b 2
