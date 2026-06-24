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
set "STAGE326_JSON=%TRAIN_DIR%\stage326_router_state_and_latency_robustness_audit.json"
set "STAGE326_SCENARIOS=%TRAIN_DIR%\stage326_router_operational_scenarios.csv"
set "STAGE326_TRACE=%TRAIN_DIR%\stage326_router_operational_decision_trace.csv"
set "OUTPUT_JSON=%TRAIN_DIR%\stage326a_router_disagreement_counter_correction_audit.json"
set "CORRECTED_SCENARIOS=%TRAIN_DIR%\stage326a_corrected_router_operational_scenarios.csv"
set "CORRECTED_TRACE=%TRAIN_DIR%\stage326a_corrected_take_disagreement_trace.csv"
echo Running Stage326A router disagreement counter correction audit...
%PYTHON_CMD% "%RUNTIME%\gold_v3_326a_router_disagreement_counter_correction_audit.py" --stage326-json "%STAGE326_JSON%" --stage326-scenarios "%STAGE326_SCENARIOS%" --stage326-trace "%STAGE326_TRACE%" --output "%OUTPUT_JSON%" --corrected-scenarios-csv "%CORRECTED_SCENARIOS%" --corrected-trace-csv "%CORRECTED_TRACE%"
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo Corrected scenario summary:
echo %CORRECTED_SCENARIOS%
echo Corrected disagreement trace:
echo %CORRECTED_TRACE%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage326A did not complete. Review the console message.
pause
exit /b %RC%
