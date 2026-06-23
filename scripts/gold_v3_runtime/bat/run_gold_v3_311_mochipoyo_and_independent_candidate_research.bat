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
set "OUTPUT_JSON=%TRAIN_DIR%\stage311_mochipoyo_and_independent_candidate_research.json"
set "TRADES_CSV=%TRAIN_DIR%\stage311_candidate_research_all_trades.csv"
set "SELECTED_CSV=%TRAIN_DIR%\stage311_selected_lead_trades.csv"
set "STAGE309_CSV=%TRAIN_DIR%\stage309_stage307_top_candidate_trades.csv"
echo Running Stage311 candidate research...
%PYTHON_CMD% "%RUNTIME%\gold_v3_311_mochipoyo_and_independent_candidate_research.py" --candle-dir "%TRAIN_DIR%" --output "%OUTPUT_JSON%" --trades-csv "%TRADES_CSV%" --selected-trades-csv "%SELECTED_CSV%" --stage309-trades "%STAGE309_CSV%" --point-size 0.01 --top 250
set "RC=%ERRORLEVEL%"
echo.
echo %OUTPUT_JSON%
echo %TRADES_CSV%
echo %SELECTED_CSV%
pause
exit /b %RC%
