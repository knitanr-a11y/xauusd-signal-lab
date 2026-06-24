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
set "STAGE321_JSON=%TRAIN_DIR%\stage321_robust_profile_portfolio_overlap_audit.json"
set "STAGE321_SELECTED=%TRAIN_DIR%\stage321_selected_shadow_portfolio_trades.csv"
set "OUTPUT_JSON=%TRAIN_DIR%\stage322_win_rate_first_shadow_selection_audit.json"
set "LEADERBOARD_CSV=%TRAIN_DIR%\stage322_win_rate_first_shadow_leaderboard.csv"
set "SELECTED_CSV=%TRAIN_DIR%\stage322_selected_conservative_shadow_trades.csv"
echo Running Stage322 win-rate-first shadow selection audit...
%PYTHON_CMD% "%RUNTIME%\gold_v3_322_win_rate_first_shadow_selection_audit.py" --stage321-json "%STAGE321_JSON%" --stage321-selected "%STAGE321_SELECTED%" --output "%OUTPUT_JSON%" --leaderboard-csv "%LEADERBOARD_CSV%" --selected-csv "%SELECTED_CSV%"
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo Win-rate-first leaderboard:
echo %LEADERBOARD_CSV%
echo Selected conservative shadow trades:
echo %SELECTED_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage322 did not complete. Review the console message.
pause
exit /b %RC%
