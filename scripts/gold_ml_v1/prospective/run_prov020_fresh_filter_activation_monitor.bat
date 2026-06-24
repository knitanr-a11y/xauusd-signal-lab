@echo off
setlocal EnableExtensions

if "%~1"=="" (
  echo ERROR: exact prospective GML1-PROV-015 parent-event CSV is required.
  echo Usage: %~nx0 PARENT_EVENTS_CSV [LEDGER_JSONL] [SUMMARY_JSON]
  exit /b 2
)

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
set "LEDGER=%~2"
set "SUMMARY=%~3"
if "%LEDGER%"=="" set "LEDGER=%REPO_ROOT%\FX_OUTPUTS\gold_ml_v1\prospective\GML1-PROV-020\filter_activation_ledger.jsonl"
if "%SUMMARY%"=="" set "SUMMARY=%REPO_ROOT%\FX_OUTPUTS\gold_ml_v1\prospective\GML1-PROV-020\filter_activation_summary.json"

python "%SCRIPT_DIR%prov020_fresh_filter_activation_monitor.py" ^
  --config "%REPO_ROOT%\config\gold_ml_v1\prov020_fresh_filter_activation_monitor_20260624.json" ^
  --parent-events "%~1" ^
  --ledger "%LEDGER%" ^
  --summary "%SUMMARY%"

exit /b %ERRORLEVEL%
