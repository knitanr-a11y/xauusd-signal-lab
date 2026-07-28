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

if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"

echo [BTC_ML_V1_01] fresh-forward availability read-only audit
echo [BTC_ML_V1_01] repo_root=%REPO_ROOT%
echo [BTC_ML_V1_01] output_root=%OUTPUT_ROOT%
echo [BTC_ML_V1_01] external actions remain OFF: candidate_engine=false evaluator=false collector=false Discord=false MT5=false live_ready=false final_signal=false

echo.
python scripts\btc_ml_v1\fresh_forward_availability\python\audit_btc_fresh_forward_availability.py --output-root "%OUTPUT_ROOT%" %*
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo [BTC_ML_V1_01] exit_code=%EXIT_CODE%
echo [BTC_ML_V1_01] latest=%OUTPUT_ROOT%\LATEST

if not "%EXIT_CODE%"=="0" (
  echo [BTC_ML_V1_01] BLOCKED or FAILED. Stop here and check LATEST\02_availability_report.txt if it exists.
  exit /b %EXIT_CODE%
)

echo [BTC_ML_V1_01] SUCCESS: availability audit complete.
echo [BTC_ML_V1_01] Upload only LATEST\99_UPLOAD_PACKAGE.zip.
echo [BTC_ML_V1_01] Fresh performance evaluation was not run.
exit /b 0
