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
set "STAGE327_JSON=%TRAIN_DIR%\stage327_persistent_router_state_checkpoint_restart_parity_audit.json"
set "STAGE327_TERMINAL=%TRAIN_DIR%\stage327_router_terminal_state_snapshot.json"
set "STAGE326A_JSON=%TRAIN_DIR%\stage326a_router_disagreement_counter_correction_audit.json"
set "STAGE324_TIMELINE=%TRAIN_DIR%\stage324_membership_regime_timeline.csv"
set "STAGE318_JSON=%TRAIN_DIR%\stage318_mochipoyo_high_confidence_refinement.json"
set "STAGE319_CONTRACT=%TRAIN_DIR%\stage319_mochipoyo_dual_tier_prospective_watch_contract.json"
set "CONTRACT_JSON=%TRAIN_DIR%\stage328_persistent_router_prospective_shadow_contract.json"
set "BOOTSTRAP_JSON=%TRAIN_DIR%\stage328_persistent_router_bootstrap_state.json"
set "OUTPUT_JSON=%TRAIN_DIR%\stage328_persistent_router_prospective_shadow_watch.json"
echo Running Stage328 persistent router prospective shadow contract freeze...
%PYTHON_CMD% "%RUNTIME%\gold_v3_328_persistent_router_prospective_shadow_contract.py" --stage327-json "%STAGE327_JSON%" --stage327-terminal-state "%STAGE327_TERMINAL%" --stage326a-json "%STAGE326A_JSON%" --stage324-timeline "%STAGE324_TIMELINE%" --stage318-json "%STAGE318_JSON%" --stage319-contract "%STAGE319_CONTRACT%" --contract "%CONTRACT_JSON%" --bootstrap-state "%BOOTSTRAP_JSON%" --output "%OUTPUT_JSON%"
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo Frozen contract:
echo %CONTRACT_JSON%
echo Frozen bootstrap state:
echo %BOOTSTRAP_JSON%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage328 did not complete. Review the console message.
pause
exit /b %RC%
