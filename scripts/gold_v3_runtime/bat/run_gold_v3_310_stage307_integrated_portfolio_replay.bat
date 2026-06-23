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
set "OUTPUT_JSON=%TRAIN_DIR%\stage310_stage307_integrated_portfolio_replay.json"
set "ACCEPTED_CSV=%TRAIN_DIR%\stage310_stage307_integrated_accepted.csv"
set "REJECTED_CSV=%TRAIN_DIR%\stage310_stage307_integrated_rejected.csv"
echo [INFO] Running Stage310 Stage307 integrated one-position replay...
%PYTHON_CMD% "%RUNTIME%\gold_v3_310_stage307_integrated_portfolio_replay.py" --candle-dir "%TRAIN_DIR%" --output "%OUTPUT_JSON%" --accepted-csv "%ACCEPTED_CSV%" --rejected-csv "%REJECTED_CSV%"
set "RC=%ERRORLEVEL%"
echo.
echo Result JSON:
echo %OUTPUT_JSON%
echo Accepted replay CSV:
echo %ACCEPTED_CSV%
echo Rejected overlap CSV:
echo %REJECTED_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage310 could not complete. Review the JSON or console message.
pause
exit /b %RC%
