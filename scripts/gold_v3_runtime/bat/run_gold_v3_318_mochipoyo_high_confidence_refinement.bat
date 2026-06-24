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
set "STAGE317_JSON=%TRAIN_DIR%\stage317_unified_mochipoyo_pool_audit.json"
set "STAGE317_SELECTED=%TRAIN_DIR%\stage317_selected_unified_mochipoyo_trades.csv"
set "OUTPUT_JSON=%TRAIN_DIR%\stage318_mochipoyo_high_confidence_refinement.json"
set "ALL_CSV=%TRAIN_DIR%\stage318_mochipoyo_high_confidence_all_profiles.csv"
set "PRIMARY_CSV=%TRAIN_DIR%\stage318_primary_high_confidence_trades.csv"
set "SPARSE_CSV=%TRAIN_DIR%\stage318_premium_sparse_watch_trades.csv"
echo Running Stage318 Mochipoyo high-confidence refinement...
%PYTHON_CMD% "%RUNTIME%\gold_v3_318_mochipoyo_high_confidence_refinement.py" --stage317-json "%STAGE317_JSON%" --stage317-selected "%STAGE317_SELECTED%" --output "%OUTPUT_JSON%" --all-profiles-csv "%ALL_CSV%" --primary-csv "%PRIMARY_CSV%" --sparse-csv "%SPARSE_CSV%"
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo All fixed profiles:
echo %ALL_CSV%
echo Primary high-confidence candidate:
echo %PRIMARY_CSV%
echo Premium sparse watch:
echo %SPARSE_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage318 did not complete. Review the console message.
pause
exit /b %RC%
