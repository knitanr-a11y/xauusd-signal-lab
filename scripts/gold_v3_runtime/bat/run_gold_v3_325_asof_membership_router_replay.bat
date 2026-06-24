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
set "STAGE324_JSON=%TRAIN_DIR%\stage324_membership_regime_rotation_audit.json"
set "STAGE324_TIMELINE=%TRAIN_DIR%\stage324_membership_regime_timeline.csv"
set "OUTPUT_JSON=%TRAIN_DIR%\stage325_asof_membership_router_replay.json"
set "LEADERBOARD_CSV=%TRAIN_DIR%\stage325_asof_membership_router_leaderboard.csv"
set "SELECTED_TRADES_CSV=%TRAIN_DIR%\stage325_selected_asof_router_trades.csv"
set "DECISION_TRACE_CSV=%TRAIN_DIR%\stage325_selected_asof_router_decision_trace.csv"
echo Running Stage325 resolved-only as-of membership router replay...
%PYTHON_CMD% "%RUNTIME%\gold_v3_325_asof_membership_router_replay.py" --stage324-json "%STAGE324_JSON%" --stage324-timeline "%STAGE324_TIMELINE%" --output "%OUTPUT_JSON%" --leaderboard-csv "%LEADERBOARD_CSV%" --selected-trades-csv "%SELECTED_TRADES_CSV%" --decision-trace-csv "%DECISION_TRACE_CSV%"
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo Router leaderboard:
echo %LEADERBOARD_CSV%
echo Selected router trades:
echo %SELECTED_TRADES_CSV%
echo Selected router decision trace:
echo %DECISION_TRACE_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage325 did not complete. Review the console message.
pause
exit /b %RC%
