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
set "STAGE322_JSON=%TRAIN_DIR%\stage322_win_rate_first_shadow_selection_audit.json"
set "STAGE322_SELECTED=%TRAIN_DIR%\stage322_selected_conservative_shadow_trades.csv"
set "OUTPUT_JSON=%TRAIN_DIR%\stage323_conservative_shadow_execution_cost_stress_audit.json"
set "SCENARIO_CSV=%TRAIN_DIR%\stage323_execution_cost_stress_scenarios.csv"
set "STRESSED_TRADES_CSV=%TRAIN_DIR%\stage323_execution_cost_stressed_trades.csv"
echo Running Stage323 conservative shadow execution cost stress audit...
%PYTHON_CMD% "%RUNTIME%\gold_v3_323_conservative_shadow_execution_cost_stress_audit.py" --stage322-json "%STAGE322_JSON%" --stage322-selected "%STAGE322_SELECTED%" --output "%OUTPUT_JSON%" --scenario-csv "%SCENARIO_CSV%" --stressed-trades-csv "%STRESSED_TRADES_CSV%"
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo Scenario summary:
echo %SCENARIO_CSV%
echo Stressed trade registry:
echo %STRESSED_TRADES_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage323 did not complete. Review the console message.
pause
exit /b %RC%
