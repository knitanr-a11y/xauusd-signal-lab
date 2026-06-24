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
set "STAGE323_JSON=%TRAIN_DIR%\stage323_conservative_shadow_execution_cost_stress_audit.json"
set "STAGE323_TRADES=%TRAIN_DIR%\stage323_execution_cost_stressed_trades.csv"
set "OUTPUT_JSON=%TRAIN_DIR%\stage324_membership_regime_rotation_audit.json"
set "GROUP_SUMMARY_CSV=%TRAIN_DIR%\stage324_membership_regime_group_summary.csv"
set "TIMELINE_CSV=%TRAIN_DIR%\stage324_membership_regime_timeline.csv"
echo Running Stage324 membership regime rotation audit...
%PYTHON_CMD% "%RUNTIME%\gold_v3_324_membership_regime_rotation_audit.py" --stage323-json "%STAGE323_JSON%" --stage323-trades "%STAGE323_TRADES%" --output "%OUTPUT_JSON%" --group-summary-csv "%GROUP_SUMMARY_CSV%" --timeline-csv "%TIMELINE_CSV%"
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo Group summary:
echo %GROUP_SUMMARY_CSV%
echo Membership timeline:
echo %TIMELINE_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage324 did not complete. Review the console message.
pause
exit /b %RC%
