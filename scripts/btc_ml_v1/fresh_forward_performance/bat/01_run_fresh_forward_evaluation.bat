@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"
if defined LOCALAPPDATA (
  set "OUTPUT_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\02_fresh_forward_performance"
) else (
  set "OUTPUT_ROOT=%TEMP%\xauusd_signal_lab\btc_ml_v1\outputs\02_fresh_forward_performance"
)
set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  echo [BTC_FF02] FAILED: Python was not found.
  pause
  exit /b 9009
)
%PYTHON_CMD% -c "import numpy, pandas" >nul 2>&1
if errorlevel 1 (
  echo [BTC_FF02] FAILED: numpy or pandas is unavailable.
  pause
  exit /b 3
)
if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"
echo [BTC_FF02] Frozen-five fresh-forward performance evaluation
echo [BTC_FF02] cutoff_utc_exclusive=2026-07-02 02:15:00
echo [BTC_FF02] candidate_rules=frozen source_csv=read_only
echo [BTC_FF02] This may take several minutes. Do not start another copy.
echo.
%PYTHON_CMD% "scripts\btc_ml_v1\fresh_forward_performance\python\evaluate_btc_fresh_forward_performance.py" --output-root "%OUTPUT_ROOT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
set "LATEST_DIR=%OUTPUT_ROOT%\LATEST"
set "UPLOAD_ZIP=%LATEST_DIR%\99_UPLOAD_PACKAGE.zip"
set "PACKAGE_OK=1"
for %%F in (
  "00_READ_ME_FIRST.txt"
  "01_fresh_forward_summary.json"
  "02_fresh_forward_report.txt"
  "03_fresh_forward_trade_ledger.csv"
  "04_candidate_metrics.csv"
  "05_monthly_metrics.csv"
  "06_direction_metrics.csv"
  "07_input_manifest.csv"
  "08_candidate_engine_manifest.csv"
  "99_UPLOAD_PACKAGE.zip"
) do if not exist "%LATEST_DIR%\%%~F" (
  echo [BTC_FF02] Missing output: %%~F
  set "PACKAGE_OK=0"
)
if "%PACKAGE_OK%"=="1" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "$null=Get-Content -Raw -LiteralPath '%LATEST_DIR%\01_fresh_forward_summary.json'|ConvertFrom-Json;" ^
    "Add-Type -AssemblyName System.IO.Compression.FileSystem;" ^
    "$z=[System.IO.Compression.ZipFile]::OpenRead('%UPLOAD_ZIP%');" ^
    "$expected=@('00_READ_ME_FIRST.txt','01_fresh_forward_summary.json','02_fresh_forward_report.txt','03_fresh_forward_trade_ledger.csv','04_candidate_metrics.csv','05_monthly_metrics.csv','06_direction_metrics.csv','07_input_manifest.csv','08_candidate_engine_manifest.csv');" ^
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
echo [BTC_FF02] exit_code=%EXIT_CODE%
if not "%PACKAGE_OK%"=="1" (
  echo [BTC_FF02] FAILED: output package validation failed.
  pause
  exit /b 4
)
if not "%EXIT_CODE%"=="0" (
  echo [BTC_FF02] BLOCKED or FAILED. Upload the ZIP for review and stop.
  pause
  exit /b %EXIT_CODE%
)
echo [BTC_FF02] Completed. Upload only 99_UPLOAD_PACKAGE.zip and stop.
pause
exit /b 0
