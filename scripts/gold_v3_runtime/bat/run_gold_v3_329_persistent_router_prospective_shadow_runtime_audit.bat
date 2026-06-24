@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\..\..\.."
set "RUNTIME=%CD%\scripts\gold_v3_runtime"
set "FILES_DIR="
if defined GOLD_V3_MQL5_FILES set "FILES_DIR=%GOLD_V3_MQL5_FILES%"
if not defined FILES_DIR (
  for /d %%D in ("%APPDATA%\MetaQuotes\Terminal\*") do (
    if not defined FILES_DIR (
      set "CANDIDATE=%%~fD\MQL5\Files"
      if exist "!CANDIDATE!\FX_OUTPUTS\gold_v3\289_training_history\goldsharp_m1.csv" set "FILES_DIR=!CANDIDATE!"
    )
  )
)
if not defined FILES_DIR (
  echo [BLOCKED] Stage289 training-history folder was not found.
  pause
  exit /b 2
)
where python >nul 2>&1
if not errorlevel 1 (set "PYTHON_CMD=python") else (set "PYTHON_CMD=py -3")
set "TRAIN_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v3\289_training_history"
set "CONTRACT_JSON=%TRAIN_DIR%\stage328_persistent_router_prospective_shadow_contract.json"
set "BOOTSTRAP_JSON=%TRAIN_DIR%\stage328_persistent_router_bootstrap_state.json"
set "RUNTIME_STATE_JSON=%TRAIN_DIR%\stage329_persistent_router_runtime_state.json"
set "JOURNAL_CSV=%TRAIN_DIR%\stage329_persistent_router_state_journal.csv"
set "OUTPUT_JSON=%TRAIN_DIR%\stage329_persistent_router_prospective_shadow_watch.json"
set "RAW_CSV=%TRAIN_DIR%\stage329_persistent_router_raw_signals.csv"
set "CANONICAL_CSV=%TRAIN_DIR%\stage329_persistent_router_canonical_source_signals.csv"
set "SOURCE_PENDING_CSV=%TRAIN_DIR%\stage329_persistent_router_source_pending.csv"
set "SOURCE_RESOLVED_CSV=%TRAIN_DIR%\stage329_persistent_router_source_resolved.csv"
set "SELECTED_CSV=%TRAIN_DIR%\stage329_persistent_router_selected_signals.csv"
set "SELECTED_PENDING_CSV=%TRAIN_DIR%\stage329_persistent_router_selected_pending.csv"
set "SELECTED_RESOLVED_CSV=%TRAIN_DIR%\stage329_persistent_router_selected_resolved.csv"
set "REJECTED_OVERLAP_CSV=%TRAIN_DIR%\stage329_persistent_router_rejected_overlap.csv"
set "HEALTH_CSV=%TRAIN_DIR%\stage329_persistent_router_health.csv"
if not exist "%CONTRACT_JSON%" (
  echo [BLOCKED] Frozen Stage328 contract is missing: %CONTRACT_JSON%
  pause
  exit /b 2
)
if not exist "%BOOTSTRAP_JSON%" (
  echo [BLOCKED] Frozen Stage328 bootstrap is missing: %BOOTSTRAP_JSON%
  pause
  exit /b 2
)
echo Running Stage329 persistent router prospective shadow runtime audit-only...
%PYTHON_CMD% "%RUNTIME%\gold_v3_329_persistent_router_prospective_shadow_runtime_audit.py" --candle-dir "%TRAIN_DIR%" --contract "%CONTRACT_JSON%" --bootstrap-state "%BOOTSTRAP_JSON%" --runtime-state "%RUNTIME_STATE_JSON%" --journal-csv "%JOURNAL_CSV%" --output "%OUTPUT_JSON%" --raw-signals-csv "%RAW_CSV%" --canonical-signals-csv "%CANONICAL_CSV%" --source-pending-csv "%SOURCE_PENDING_CSV%" --source-resolved-csv "%SOURCE_RESOLVED_CSV%" --selected-signals-csv "%SELECTED_CSV%" --selected-pending-csv "%SELECTED_PENDING_CSV%" --selected-resolved-csv "%SELECTED_RESOLVED_CSV%" --rejected-overlap-csv "%REJECTED_OVERLAP_CSV%" --health-csv "%HEALTH_CSV%"
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo Mutable runtime state:
echo %RUNTIME_STATE_JSON%
echo Append-only journal:
echo %JOURNAL_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage329 did not complete. Review the console message. Frozen Stage328 files were not changed.
pause
exit /b %RC%
