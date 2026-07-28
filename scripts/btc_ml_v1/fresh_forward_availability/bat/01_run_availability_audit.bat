@echo off
setlocal EnableExtensions DisableDelayedExpansion

REM BTC ML V1 FF01 fresh-forward availability read-only audit.
REM User-facing launcher. Do not run multiple copies at the same time.

set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if defined LOCALAPPDATA (
  set "OUTPUT_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability"
) else (
  set "OUTPUT_ROOT=%TEMP%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability"
)

set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  echo [BTC_FF01] FAILED: Python was not found.
  echo [BTC_FF01] Install or restore Python, then run this BAT again.
  echo [BTC_FF01] No collector, M7C, M8C, GOLD, Discord or MT5 action was started.
  echo.
  pause
  exit /b 9009
)

if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"

echo [BTC_FF01] Fresh-forward availability read-only audit
echo [BTC_FF01] repo_root=%REPO_ROOT%
echo [BTC_FF01] output_root=%OUTPUT_ROOT%
echo [BTC_FF01] source_csv=READ_ONLY
echo [BTC_FF01] evaluator=false candidate_engine=false collector=false Discord=false MT5=false live_ready=false final_signal=false
echo.

%PYTHON_CMD% "scripts\btc_ml_v1\fresh_forward_availability\python\audit_btc_fresh_forward_availability.py" --output-root "%OUTPUT_ROOT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
set "LATEST_DIR=%OUTPUT_ROOT%\LATEST"

echo.
echo [BTC_FF01] exit_code=%EXIT_CODE%
echo [BTC_FF01] latest=%LATEST_DIR%

if exist "%LATEST_DIR%" (
  start "" explorer.exe "%LATEST_DIR%"
  echo [BTC_FF01] Opened LATEST results folder.
) else (
  echo [BTC_FF01] LATEST folder was not created.
)

if not "%EXIT_CODE%"=="0" (
  echo [BTC_FF01] BLOCKED or FAILED. Stop here.
  echo [BTC_FF01] Check LATEST\02_availability_report.txt if it exists.
  echo [BTC_FF01] Do not run FF02 or any evaluator.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [BTC_FF01] Audit package creation completed.
echo [BTC_FF01] Candidate-specific READY or BLOCKED is recorded in the report.
echo [BTC_FF01] Upload only LATEST\99_UPLOAD_PACKAGE.zip.
echo [BTC_FF01] Stop after package upload. FF02 is not authorized.
echo.
pause
exit /b 0
