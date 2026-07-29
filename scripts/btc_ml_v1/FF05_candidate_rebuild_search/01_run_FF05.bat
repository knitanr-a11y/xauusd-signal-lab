@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if defined LOCALAPPDATA (
  set "OUTPUT_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\FF05_candidate_rebuild_search"
) else (
  set "OUTPUT_ROOT=%TEMP%\xauusd_signal_lab\btc_ml_v1\outputs\FF05_candidate_rebuild_search"
)

set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  echo [BTC_FF05] FAILED: Python was not found.
  pause
  exit /b 9009
)

%PYTHON_CMD% -c "import numpy, pandas" >nul 2>&1
if errorlevel 1 (
  echo [BTC_FF05] FAILED: numpy or pandas is unavailable.
  pause
  exit /b 3
)

if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"
set "PYTHONHASHSEED=0"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"

echo [BTC_FF05] Causal candidate rebuild search
echo [BTC_FF05] Exactly 108 preregistered cells will be evaluated.
echo [BTC_FF05] CSV time is BAR OPEN time. Exact M5 entry is mandatory.
echo [BTC_FF05] FF02 six losses are excluded from tuning.
echo [BTC_FF05] This can take several minutes. Do not start another copy.
echo [BTC_FF05] Source CSV is read-only. No live or order action is enabled.
echo.

%PYTHON_CMD% "scripts\btc_ml_v1\FF05_candidate_rebuild_search\python\run_FF05_candidate_rebuild_search.py" --output-root "%OUTPUT_ROOT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
set "LATEST_DIR=%OUTPUT_ROOT%\LATEST"
set "UPLOAD_ZIP=%LATEST_DIR%\99_UPLOAD_PACKAGE.zip"
set "PACKAGE_OK=1"

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
  "99_UPLOAD_PACKAGE.zip"
) do if not exist "%LATEST_DIR%\%%~F" (
  echo [BTC_FF05] Missing output: %%~F
  set "PACKAGE_OK=0"
)

if "%PACKAGE_OK%"=="1" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "$s=Get-Content -Raw -LiteralPath '%LATEST_DIR%\01_search_summary.json'|ConvertFrom-Json;" ^
    "if(-not $s.search_complete -and $null -eq $s.fatal_error){throw 'incomplete summary without fatal error'};" ^
    "Add-Type -AssemblyName System.IO.Compression.FileSystem;" ^
    "$z=[System.IO.Compression.ZipFile]::OpenRead('%UPLOAD_ZIP%');" ^
    "$expected=@('00_READ_ME_FIRST.txt','01_search_summary.json','02_search_report.txt','03_all_108_cells.csv','04_oos_segment_metrics.csv','05_trade_ledger.csv','06_weekly_block_matrix.csv','07_bootstrap_familywise.csv','08_input_manifest.csv','09_selected_candidate.json','10_preregistration_copy.json','11_self_tests.csv');" ^
    "$actual=@($z.Entries|ForEach-Object FullName);$z.Dispose();" ^
    "if(($actual.Count-ne$expected.Count)-or(Compare-Object $expected $actual)){throw 'ZIP validation failed'}"
  if errorlevel 1 set "PACKAGE_OK=0"
)

if exist "%UPLOAD_ZIP%" (
  start "" explorer.exe /select,"%UPLOAD_ZIP%"
) else if exist "%LATEST_DIR%" (
  start "" explorer.exe "%LATEST_DIR%"
)

echo.
echo [BTC_FF05] exit_code=%EXIT_CODE%
if not "%PACKAGE_OK%"=="1" (
  echo [BTC_FF05] FAILED: output package validation failed.
  pause
  exit /b 4
)
if not "%EXIT_CODE%"=="0" (
  echo [BTC_FF05] BLOCKED or FAILED. Upload the ZIP for review and stop.
  pause
  exit /b %EXIT_CODE%
)

echo [BTC_FF05] Completed. Upload only 99_UPLOAD_PACKAGE.zip and stop.
pause
exit /b 0
