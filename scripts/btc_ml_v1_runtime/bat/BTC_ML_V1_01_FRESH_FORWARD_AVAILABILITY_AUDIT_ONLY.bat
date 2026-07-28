@echo off
setlocal EnableExtensions DisableDelayedExpansion

REM BTC ML V1 01 fresh-forward availability audit-only.
REM Location: scripts\btc_ml_v1_runtime\bat\BTC_ML_V1_01_FRESH_FORWARD_AVAILABILITY_AUDIT_ONLY.bat
REM Output: Files\FX_OUTPUTS\btc_ml_v1\01_fresh_forward_availability_audit_only
REM Read-only CSV audit only. No candidate evaluation, collector, Discord, MT5 order,
REM live_ready, final_signal, lot design, or new-candidate exploration.

set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "OUTPUT_DIR=%REPO_ROOT%\Files\FX_OUTPUTS\btc_ml_v1\01_fresh_forward_availability_audit_only"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [BTC_ML_V1_01] fresh-forward availability read-only audit
echo [BTC_ML_V1_01] repo_root=%REPO_ROOT%
echo [BTC_ML_V1_01] output_dir=%OUTPUT_DIR%
echo [BTC_ML_V1_01] external actions remain OFF: Discord=false MT5=false live_ready=false final_signal=false

python scripts\btc_ml_v1\research\audit_btc_fresh_forward_availability.py %* --output-dir "%OUTPUT_DIR%"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo [BTC_ML_V1_01] exit_code=%EXIT_CODE%
echo [BTC_ML_V1_01] output=%OUTPUT_DIR%

if not "%EXIT_CODE%"=="0" (
  echo [BTC_ML_V1_01] BLOCKED or FAILED. Check availability_report.txt in the output folder.
  exit /b %EXIT_CODE%
)

echo [BTC_ML_V1_01] availability audit complete. Fresh performance evaluation was not run.
exit /b 0
