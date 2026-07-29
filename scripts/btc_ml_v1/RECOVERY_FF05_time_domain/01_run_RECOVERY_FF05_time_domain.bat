@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if defined LOCALAPPDATA (
  set "OUTPUT_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\RECOVERY_FF05_time_domain"
) else (
  set "OUTPUT_ROOT=%TEMP%\xauusd_signal_lab\btc_ml_v1\outputs\RECOVERY_FF05_time_domain"
)

set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  echo [RECOVERY_FF05_TIME] FAILED: Python was not found.
  pause
  exit /b 9009
)

%PYTHON_CMD% -c "import pandas, numpy" >nul 2>&1
if errorlevel 1 (
  echo [RECOVERY_FF05_TIME] FAILED: pandas or numpy is unavailable.
  pause
  exit /b 3
)

if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"

echo [RECOVERY_FF05_TIME] Audit UTC versus MT5 broker-server timestamp domain
echo [RECOVERY_FF05_TIME] Exact OHLC is compared at shifts from -5 to +5 hours.
echo [RECOVERY_FF05_TIME] BAR OPEN time and closed-bar cutoff rules are enforced.
echo [RECOVERY_FF05_TIME] FF05 performance is NOT rerun.
echo [RECOVERY_FF05_TIME] Source CSV files are read-only.
echo.

%PYTHON_CMD% "scripts\btc_ml_v1\RECOVERY_FF05_time_domain\python\run_RECOVERY_FF05_time_domain.py" --output-root "%OUTPUT_ROOT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
set "LATEST_DIR=%OUTPUT_ROOT%\LATEST"
set "UPLOAD_ZIP=%LATEST_DIR%\99_UPLOAD_PACKAGE.zip"
set "PACKAGE_OK=1"

for %%F in (
  "00_READ_ME_FIRST.txt"
  "01_time_domain_summary.json"
  "02_time_domain_report.txt"
  "03_shift_comparison.csv"
  "04_monthly_offset_evidence.csv"
  "05_offset_runs.csv"
  "06_input_manifest.csv"
  "07_cutoff_availability.csv"
  "08_self_tests.csv"
  "99_UPLOAD_PACKAGE.zip"
) do if not exist "%LATEST_DIR%\%%~F" (
  echo [RECOVERY_FF05_TIME] Missing output: %%~F
  set "PACKAGE_OK=0"
)

if "%PACKAGE_OK%"=="1" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "$s=Get-Content -Raw -LiteralPath '%LATEST_DIR%\01_time_domain_summary.json'|ConvertFrom-Json;" ^
    "if(-not $s.audit_complete){throw 'audit_complete is false'};" ^
    "Add-Type -AssemblyName System.IO.Compression.FileSystem;" ^
    "$z=[System.IO.Compression.ZipFile]::OpenRead('%UPLOAD_ZIP%');" ^
    "$expected=@('00_READ_ME_FIRST.txt','01_time_domain_summary.json','02_time_domain_report.txt','03_shift_comparison.csv','04_monthly_offset_evidence.csv','05_offset_runs.csv','06_input_manifest.csv','07_cutoff_availability.csv','08_self_tests.csv');" ^
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
echo [RECOVERY_FF05_TIME] exit_code=%EXIT_CODE%
if not "%PACKAGE_OK%"=="1" (
  echo [RECOVERY_FF05_TIME] FAILED: output package validation failed.
  pause
  exit /b 4
)
if "%EXIT_CODE%"=="0" (
  echo [RECOVERY_FF05_TIME] Time domain was proven. Upload the ZIP and stop.
  pause
  exit /b 0
)
if "%EXIT_CODE%"=="2" (
  echo [RECOVERY_FF05_TIME] Time domain remains blocked. Upload the ZIP and stop.
  pause
  exit /b 2
)

echo [RECOVERY_FF05_TIME] FAILED unexpectedly. Upload the ZIP if it exists and stop.
pause
exit /b %EXIT_CODE%
