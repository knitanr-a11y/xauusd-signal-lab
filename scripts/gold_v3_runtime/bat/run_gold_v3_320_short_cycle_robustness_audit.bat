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
set "STAGE318_JSON=%TRAIN_DIR%\stage318_mochipoyo_high_confidence_refinement.json"
set "STAGE318_ALL=%TRAIN_DIR%\stage318_mochipoyo_high_confidence_all_profiles.csv"
set "OUTPUT_JSON=%TRAIN_DIR%\stage320_short_cycle_robustness_audit.json"
set "LEADERBOARD_CSV=%TRAIN_DIR%\stage320_short_cycle_robustness_leaderboard.csv"
set "CORE_CSV=%TRAIN_DIR%\stage320_robust_core_trades.csv"
set "BALANCED_CSV=%TRAIN_DIR%\stage320_balanced_challenger_trades.csv"
set "PREMIUM_CSV=%TRAIN_DIR%\stage320_robust_premium_trades.csv"
echo Running Stage320 short-cycle robustness audit...
%PYTHON_CMD% "%RUNTIME%\gold_v3_320_short_cycle_robustness_audit.py" --stage318-json "%STAGE318_JSON%" --stage318-all-profiles "%STAGE318_ALL%" --output "%OUTPUT_JSON%" --leaderboard-csv "%LEADERBOARD_CSV%" --core-csv "%CORE_CSV%" --balanced-csv "%BALANCED_CSV%" --premium-csv "%PREMIUM_CSV%"
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo Robustness leaderboard:
echo %LEADERBOARD_CSV%
echo Robust core:
echo %CORE_CSV%
echo Balanced challenger:
echo %BALANCED_CSV%
echo Robust premium:
echo %PREMIUM_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage320 did not complete. Review the console message.
pause
exit /b %RC%
