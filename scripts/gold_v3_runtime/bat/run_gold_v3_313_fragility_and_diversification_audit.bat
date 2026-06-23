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
if not defined FILES_DIR exit /b 2
where python >nul 2>&1
if not errorlevel 1 (set "PYTHON_CMD=python") else (set "PYTHON_CMD=py -3")
set "TRAIN_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v3\289_training_history"
set "STAGE312_JSON=%TRAIN_DIR%\stage312_near_miss_candidate_refinement.json"
set "STAGE311_TRADES=%TRAIN_DIR%\stage311_candidate_research_all_trades.csv"
set "OUTPUT_JSON=%TRAIN_DIR%\stage313_fragility_and_diversification_audit.json"
set "COMBINED_CSV=%TRAIN_DIR%\stage313_diversified_research_watch_trades.csv"
echo Running Stage313 fragility and diversification audit...
%PYTHON_CMD% "%RUNTIME%\gold_v3_313_fragility_and_diversification_audit.py" --stage312-json "%STAGE312_JSON%" --stage311-trades "%STAGE311_TRADES%" --output "%OUTPUT_JSON%" --combined-csv "%COMBINED_CSV%"
set "RC=%ERRORLEVEL%"
echo.
echo %OUTPUT_JSON%
echo %COMBINED_CSV%
pause
exit /b %RC%
