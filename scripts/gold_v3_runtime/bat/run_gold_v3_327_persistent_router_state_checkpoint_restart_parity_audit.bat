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
set "STAGE326A_JSON=%TRAIN_DIR%\stage326a_router_disagreement_counter_correction_audit.json"
set "STAGE326_JSON=%TRAIN_DIR%\stage326_router_state_and_latency_robustness_audit.json"
set "STAGE324_TIMELINE=%TRAIN_DIR%\stage324_membership_regime_timeline.csv"
set "STAGE325_SELECTED=%TRAIN_DIR%\stage325_selected_asof_router_trades.csv"
set "STAGE325_TRACE=%TRAIN_DIR%\stage325_selected_asof_router_decision_trace.csv"
set "OUTPUT_JSON=%TRAIN_DIR%\stage327_persistent_router_state_checkpoint_restart_parity_audit.json"
set "CHECKPOINT_CSV=%TRAIN_DIR%\stage327_router_restart_checkpoint_summary.csv"
set "SNAPSHOT_CSV=%TRAIN_DIR%\stage327_router_state_snapshots.csv"
set "TERMINAL_STATE_JSON=%TRAIN_DIR%\stage327_router_terminal_state_snapshot.json"
echo Running Stage327 persistent router state checkpoint/restart parity audit...
%PYTHON_CMD% "%RUNTIME%\gold_v3_327_persistent_router_state_checkpoint_restart_parity_audit.py" --stage326a-json "%STAGE326A_JSON%" --stage326-json "%STAGE326_JSON%" --stage324-timeline "%STAGE324_TIMELINE%" --stage325-selected "%STAGE325_SELECTED%" --stage325-trace "%STAGE325_TRACE%" --output "%OUTPUT_JSON%" --checkpoint-csv "%CHECKPOINT_CSV%" --snapshot-csv "%SNAPSHOT_CSV%" --terminal-state-json "%TERMINAL_STATE_JSON%"
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo Checkpoint summary:
echo %CHECKPOINT_CSV%
echo State snapshots:
echo %SNAPSHOT_CSV%
echo Terminal state snapshot:
echo %TERMINAL_STATE_JSON%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage327 did not complete. Review the console message.
pause
exit /b %RC%
