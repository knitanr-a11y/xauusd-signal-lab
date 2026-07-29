@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if defined LOCALAPPDATA (
  set "OUTPUT_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\04_bar_time_semantics_rebuild_foundation"
) else (
  set "OUTPUT_ROOT=%TEMP%\xauusd_signal_lab\btc_ml_v1\outputs\04_bar_time_semantics_rebuild_foundation"
)

set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  echo [BTC_FF04] FAILED: Python was not found.
  pause
  exit /b 9009
)

%PYTHON_CMD% -c "import pandas" >nul 2>&1
if errorlevel 1 (
  echo [BTC_FF04] FAILED: pandas is unavailable.
  pause
  exit /b 3
)

if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"

echo [BTC_FF04] Bar-time semantics and causal rebuild foundation audit
echo [BTC_FF04] CSV time must be BAR OPEN time.
echo [BTC_FF04] No candidate performance search is executed.
echo [BTC_FF04] Source CSV is read-only.
echo.

%PYTHON_CMD% "scripts\btc_ml_v1\causal_rebuild_foundation\python\audit_btc_bar_time_semantics.py" --output-root "%OUTPUT_ROOT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
set "LATEST_DIR=%OUTPUT_ROOT%\LATEST"
set "UPLOAD_ZIP=%LATEST_DIR%\99_UPLOAD_PACKAGE.zip"
set "PACKAGE_OK=1"

for %%F in (
  "00_READ_ME_FIRST.txt"
  "01_time_semantics_summary.json"
  "02_time_semantics_report.txt"
  "03_timeframe_manifest.csv"
  "04_causal_sentinel_tests.csv"
  "05_rebuild_preregistration.json"
  "06_current_engine_contract.json"
  "99_UPLOAD_PACKAGE.zip"
) do if not exist "%LATEST_DIR%\%%~F" (
  echo [BTC_FF04] Missing output: %%~F
  set "PACKAGE_OK=0"
)

if "%PACKAGE_OK%"=="1" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "$s=Get-Content -Raw -LiteralPath '%LATEST_DIR%\01_time_semantics_summary.json'|ConvertFrom-Json;" ^
    "if(-not $s.audit_complete){throw 'audit_complete is false'};" ^
    "Add-Type -AssemblyName System.IO.Compression.FileSystem;" ^
    "$z=[System.IO.Compression.ZipFile]::OpenRead('%UPLOAD_ZIP%');" ^
    "$expected=@('00_READ_ME_FIRST.txt','01_time_semantics_summary.json','02_time_semantics_report.txt','03_timeframe_manifest.csv','04_causal_sentinel_tests.csv','05_rebuild_preregistration.json','06_current_engine_contract.json');" ^
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
echo [BTC_FF04] exit_code=%EXIT_CODE%
if not "%PACKAGE_OK%"=="1" (
  echo [BTC_FF04] FAILED: output package validation failed.
  pause
  exit /b 4
)
if not "%EXIT_CODE%"=="0" (
  echo [BTC_FF04] BLOCKED or FAILED. Upload the ZIP for review and stop.
  pause
  exit /b %EXIT_CODE%
)

echo [BTC_FF04] Completed. Upload only 99_UPLOAD_PACKAGE.zip and stop.
pause
exit /b 0
