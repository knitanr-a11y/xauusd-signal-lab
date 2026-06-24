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
set "STAGE316_JSON=%TRAIN_DIR%\stage316_contextual_mochipoyo_entry_research.json"
set "STAGE311_CSV=%TRAIN_DIR%\stage311_candidate_research_all_trades.csv"
set "STAGE313_CSV=%TRAIN_DIR%\stage313_diversified_research_watch_trades.csv"
set "OUTPUT_JSON=%TRAIN_DIR%\stage317_unified_mochipoyo_pool_audit.json"
set "ALL_CSV=%TRAIN_DIR%\stage317_unified_mochipoyo_all_candidates.csv"
set "SELECTED_CSV=%TRAIN_DIR%\stage317_selected_unified_mochipoyo_trades.csv"
echo Running Stage317 unified Mochipoyo pool audit...
%PYTHON_CMD% "%RUNTIME%\gold_v3_317_unified_mochipoyo_pool_audit.py" --stage316-json "%STAGE316_JSON%" --stage311-trades "%STAGE311_CSV%" --stage313-trades "%STAGE313_CSV%" --output "%OUTPUT_JSON%" --all-candidates-csv "%ALL_CSV%" --selected-csv "%SELECTED_CSV%" --top 250
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo All pooled candidates:
echo %ALL_CSV%
echo Selected pooled candidate:
echo %SELECTED_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage317 did not complete. Review the console message.
pause
exit /b %RC%
