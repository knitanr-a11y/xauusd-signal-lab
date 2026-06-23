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
set "BACKTEST_JSON=%TRAIN_DIR%\stage305_stage280_corrected_cost_walkforward.json"
echo [INFO] Running Stage280 corrected-cost walk-forward backtest...
%PYTHON_CMD% "%RUNTIME%\gold_v3_305_stage280_corrected_cost_walkforward.py" --candle-dir "%TRAIN_DIR%" --output "%BACKTEST_JSON%" --point-size 0.01 --top 200
set "RC=%ERRORLEVEL%"
echo.
echo Backtest file:
echo %BACKTEST_JSON%
echo.
pause
exit /b %RC%
