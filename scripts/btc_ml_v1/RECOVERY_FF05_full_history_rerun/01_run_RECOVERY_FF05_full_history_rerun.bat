@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if defined LOCALAPPDATA (
  set "OUTPUT_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\RECOVERY_FF05_full_history_rerun"
) else (
  set "OUTPUT_ROOT=%TEMP%\xauusd_signal_lab\btc_ml_v1\outputs\RECOVERY_FF05_full_history_rerun"
)

set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  echo [RECOVERY_FF05_RERUN] FAILED: Python was not found.
  pause
  exit /b 9009
)

%PYTHON_CMD% -c "import pandas" >nul 2>&1
if errorlevel 1 (
  echo [RECOVERY_FF05_RERUN] FAILED: pandas is unavailable.
  pause
  exit /b 3
)

if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"

echo [RECOVERY_FF05_RERUN] Run the frozen 108-cell FF05 search on merged full history
echo [RECOVERY_FF05_RERUN] Only isolated copies of the verified merged M5/M15/H1 files may be used.
echo [RECOVERY_FF05_RERUN] CSV time remains BAR OPEN in raw MT5 broker-server time.
echo [RECOVERY_FF05_RERUN] Search cells and survivor thresholds are unchanged.
echo [RECOVERY_FF05_RERUN] This can take several minutes. Do not start another copy.
echo [RECOVERY_FF05_RERUN] No live, Discord, lot, or MT5 order action is enabled.
echo.

%PYTHON_CMD% "scripts\btc_ml_v1\RECOVERY_FF05_full_history_rerun\python\run_RECOVERY_FF05_full_history_rerun.py" --output-root "%OUTPUT_ROOT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
set "LATEST_DIR=%OUTPUT_ROOT%\LATEST"
set "UPLOAD_ZIP=%LATEST_DIR%\99_UPLOAD_PACKAGE.zip"
set "PACKAGE_OK=1"

if exist "%LATEST_DIR%\01_recovery_rerun_error.json" (
  if not exist "%UPLOAD_ZIP%" set "PACKAGE_OK=0"
) else (
  for %%F in (
    "00_READ_ME_FIRST.txt"
    "01_search_summary.json"
    "02_search_report.txt"
    "03_all_108_cells.csv"
    "04_oos_segment_metrics.csv"
    "05_trade_ledger.csv"
    "06_weekly_block_matrix.csv"
    "07_bootstrap_familywise.csv"
    "08_input_manifest.csv"
    "09_selected_candidate.json"
    "10_preregistration_copy.json"
    "11_self_tests.csv"
    "12_recovery_input_provenance.json"
    "99_UPLOAD_PACKAGE.zip"
  ) do if not exist "%LATEST_DIR%\%%~F" (
    echo [RECOVERY_FF05_RERUN] Missing output: %%F
    set "PACKAGE_OK=0"
  )
)

if "%PACKAGE_OK%"=="1" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "Add-Type -AssemblyName System.IO.Compression.FileSystem;" ^
    "$z=[System.IO.Compression.ZipFile]::OpenRead('%UPLOAD_ZIP%');" ^
    "$actual=@($z.Entries|ForEach-Object FullName);$z.Dispose();" ^
    "if(Test-Path -LiteralPath '%LATEST_DIR%\01_recovery_rerun_error.json'){" ^
      "$expected=@('00_READ_ME_FIRST.txt','01_recovery_rerun_error.json');" ^
    "}else{" ^
      "$expected=@('00_READ_ME_FIRST.txt','01_search_summary.json','02_search_report.txt','03_all_108_cells.csv','04_oos_segment_metrics.csv','05_trade_ledger.csv','06_weekly_block_matrix.csv','07_bootstrap_familywise.csv','08_input_manifest.csv','09_selected_candidate.json','10_preregistration_copy.json','11_self_tests.csv','12_recovery_input_provenance.json');" ^
    "};" ^
    "if(($actual.Count-ne$expected.Count)-or(Compare-Object $expected $actual)){throw 'ZIP validation failed'}"
  if errorlevel 1 set "PACKAGE_OK=0"
)

if exist "%UPLOAD_ZIP%" (
  start "" explorer.exe /select,"%UPLOAD_ZIP%"
) else if exist "%LATEST_DIR%" (
  start "" explorer.exe "%LATEST_DIR%"
)

echo.
echo [RECOVERY_FF05_RERUN] exit_code=%EXIT_CODE%
if not "%PACKAGE_OK%"=="1" (
  echo [RECOVERY_FF05_RERUN] FAILED: output package validation failed.
  pause
  exit /b 4
)
if "%EXIT_CODE%"=="0" (
  echo [RECOVERY_FF05_RERUN] Search completed. Upload the ZIP and stop.
  pause
  exit /b 0
)

echo [RECOVERY_FF05_RERUN] Search blocked or failed. Upload the ZIP and stop.
pause
exit /b %EXIT_CODE%
