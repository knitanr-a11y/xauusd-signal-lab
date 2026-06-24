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
set "STAGE325_JSON=%TRAIN_DIR%\stage325_asof_membership_router_replay.json"
set "STAGE324_TIMELINE=%TRAIN_DIR%\stage324_membership_regime_timeline.csv"
set "STAGE325_SELECTED=%TRAIN_DIR%\stage325_selected_asof_router_trades.csv"
set "STAGE325_TRACE=%TRAIN_DIR%\stage325_selected_asof_router_decision_trace.csv"
set "OUTPUT_JSON=%TRAIN_DIR%\stage326_router_state_and_latency_robustness_audit.json"
set "SCENARIO_CSV=%TRAIN_DIR%\stage326_router_operational_scenarios.csv"
set "TRACE_CSV=%TRAIN_DIR%\stage326_router_operational_decision_trace.csv"
echo Running Stage326 router state and latency robustness audit...
%PYTHON_CMD% "%RUNTIME%\gold_v3_326_router_state_and_latency_robustness_audit.py" --stage325-json "%STAGE325_JSON%" --stage324-timeline "%STAGE324_TIMELINE%" --stage325-selected "%STAGE325_SELECTED%" --stage325-trace "%STAGE325_TRACE%" --output "%OUTPUT_JSON%" --scenario-csv "%SCENARIO_CSV%" --decision-trace-csv "%TRACE_CSV%"
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo Scenario summary:
echo %SCENARIO_CSV%
echo Decision trace:
echo %TRACE_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage326 did not complete. Review the console message.
pause
exit /b %RC%
