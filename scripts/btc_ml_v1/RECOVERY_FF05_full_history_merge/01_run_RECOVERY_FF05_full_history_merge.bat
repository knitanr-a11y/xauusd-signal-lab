@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if defined LOCALAPPDATA (
  set "OUTPUT_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\RECOVERY_FF05_full_history_merge"
) else (
  set "OUTPUT_ROOT=%TEMP%\xauusd_signal_lab\btc_ml_v1\outputs\RECOVERY_FF05_full_history_merge"
)

set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  echo [RECOVERY_FF05_MERGE] FAILED: Python was not found.
  pause
  exit /b 9009
)

%PYTHON_CMD% -c "import pandas, numpy" >nul 2>&1
if errorlevel 1 (
  echo [RECOVERY_FF05_MERGE] FAILED: pandas or numpy is unavailable.
  pause
  exit /b 3
)

if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"

echo [RECOVERY_FF05_MERGE] Merge recovered and current BTC history
echo [RECOVERY_FF05_MERGE] Duplicate timestamps must have exact OHLC identity.
echo [RECOVERY_FF05_MERGE] CSV time remains BAR OPEN in raw MT5 broker-server time.
echo [RECOVERY_FF05_MERGE] Source CSV files are read-only.
echo [RECOVERY_FF05_MERGE] FF05 performance is NOT rerun.
echo.

%PYTHON_CMD% "scripts\btc_ml_v1\RECOVERY_FF05_full_history_merge\python\run_RECOVERY_FF05_full_history_merge.py" --output-root "%OUTPUT_ROOT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
set "LATEST_DIR=%OUTPUT_ROOT%\LATEST"
set "UPLOAD_ZIP=%LATEST_DIR%\99_UPLOAD_PACKAGE.zip"
set "PACKAGE_OK=1"

for %%F in (
  "00_READ_ME_FIRST.txt"
  "01_merge_summary.json"
  "02_merge_report.txt"
  "03_merge_manifest.csv"
  "04_overlap_verification.csv"
  "05_cutoff_coverage.csv"
  "06_self_tests.csv"
  "99_UPLOAD_PACKAGE.zip"
) do if not exist "%LATEST_DIR%\%%~F" (
  echo [RECOVERY_FF05_MERGE] Missing output: %%~F
  set "PACKAGE_OK=0"
)

if "%PACKAGE_OK%"=="1" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "$s=Get-Content -Raw -LiteralPath '%LATEST_DIR%\01_merge_summary.json'|ConvertFrom-Json;" ^
    "if(-not $s.merge_complete){throw 'merge_complete is false'};" ^
    "Add-Type -AssemblyName System.IO.Compression.FileSystem;" ^
    "$z=[System.IO.Compression.ZipFile]::OpenRead('%UPLOAD_ZIP%');" ^
    "$expected=@('00_READ_ME_FIRST.txt','01_merge_summary.json','02_merge_report.txt','03_merge_manifest.csv','04_overlap_verification.csv','05_cutoff_coverage.csv','06_self_tests.csv');" ^
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
echo [RECOVERY_FF05_MERGE] exit_code=%EXIT_CODE%
if not "%PACKAGE_OK%"=="1" (
  echo [RECOVERY_FF05_MERGE] FAILED: output package validation failed.
  pause
  exit /b 4
)
if "%EXIT_CODE%"=="0" (
  echo [RECOVERY_FF05_MERGE] Full history was merged. Upload the ZIP and stop.
  pause
  exit /b 0
)
if "%EXIT_CODE%"=="2" (
  echo [RECOVERY_FF05_MERGE] Merge remains blocked. Upload the ZIP and stop.
  pause
  exit /b 2
)

echo [RECOVERY_FF05_MERGE] FAILED unexpectedly. Upload the ZIP if it exists and stop.
pause
exit /b %EXIT_CODE%
