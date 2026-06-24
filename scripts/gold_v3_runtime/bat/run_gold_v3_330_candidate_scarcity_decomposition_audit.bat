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
set "STAGE329_WATCH=%TRAIN_DIR%\stage329_persistent_router_prospective_shadow_watch.json"
set "OUTPUT_JSON=%TRAIN_DIR%\stage330_candidate_scarcity_decomposition.json"
set "FLOW_CSV=%TRAIN_DIR%\stage330_candidate_scarcity_flow.csv"
set "SUMMARY_CSV=%TRAIN_DIR%\stage330_candidate_variant_summary.csv"
set "NEAR_MISS_CSV=%TRAIN_DIR%\stage330_candidate_near_miss.csv"
set "INCREMENTAL_CSV=%TRAIN_DIR%\stage330_candidate_incremental_trades.csv"
set "CONTEXT_CSV=%TRAIN_DIR%\stage330_candidate_context_summary.csv"
if not exist "%STAGE329_WATCH%" (
  echo [BLOCKED] Stage329 audited watch JSON is missing: %STAGE329_WATCH%
  pause
  exit /b 2
)
echo Running Stage330 candidate scarcity decomposition audit-only...
%PYTHON_CMD% "%RUNTIME%\gold_v3_330_candidate_scarcity_decomposition_audit.py" --candle-dir "%TRAIN_DIR%" --stage329-watch "%STAGE329_WATCH%" --output "%OUTPUT_JSON%" --flow-csv "%FLOW_CSV%" --variant-summary-csv "%SUMMARY_CSV%" --near-miss-csv "%NEAR_MISS_CSV%" --incremental-trades-csv "%INCREMENTAL_CSV%" --context-summary-csv "%CONTEXT_CSV%"
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo Variant summary:
echo %SUMMARY_CSV%
echo Near-miss detail:
echo %NEAR_MISS_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage330 did not complete. Stage329 runtime state and journal were not changed.
pause
exit /b %RC%
