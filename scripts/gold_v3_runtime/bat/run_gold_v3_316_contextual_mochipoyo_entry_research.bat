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
set "OUTPUT_JSON=%TRAIN_DIR%\stage316_contextual_mochipoyo_entry_research.json"
set "TRADES_CSV=%TRAIN_DIR%\stage316_contextual_mochipoyo_all_trades.csv"
set "SELECTED_CSV=%TRAIN_DIR%\stage316_selected_contextual_mochipoyo_trades.csv"
set "STAGE311_CSV=%TRAIN_DIR%\stage311_candidate_research_all_trades.csv"
set "STAGE309_CSV=%TRAIN_DIR%\stage309_stage307_top_candidate_trades.csv"
set "STAGE313_CSV=%TRAIN_DIR%\stage313_diversified_research_watch_trades.csv"
set "STAGE315_CSV=%TRAIN_DIR%\stage315_selected_independent_portfolio_trades.csv"
echo Running Stage316 contextual Mochipoyo entry research...
%PYTHON_CMD% "%RUNTIME%\gold_v3_316_contextual_mochipoyo_entry_research.py" --candle-dir "%TRAIN_DIR%" --output "%OUTPUT_JSON%" --trades-csv "%TRADES_CSV%" --selected-csv "%SELECTED_CSV%" --stage311-trades "%STAGE311_CSV%" --stage309-trades "%STAGE309_CSV%" --stage313-trades "%STAGE313_CSV%" --stage315-trades "%STAGE315_CSV%" --point-size 0.01 --top 250
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo All trades:
echo %TRADES_CSV%
echo Selected contextual portfolio:
echo %SELECTED_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage316 did not complete. Review the console message.
pause
exit /b %RC%
