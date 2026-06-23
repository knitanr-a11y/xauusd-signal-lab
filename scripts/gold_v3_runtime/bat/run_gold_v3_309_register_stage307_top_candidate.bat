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
set "OUTPUT_JSON=%TRAIN_DIR%\stage309_stage307_top_candidate_registry.json"
set "TRADES_CSV=%TRAIN_DIR%\stage309_stage307_top_candidate_trades.csv"
echo [INFO] Registering Stage307 top ensemble as an audit-only research candidate...
%PYTHON_CMD% "%RUNTIME%\gold_v3_309_register_stage307_top_candidate.py" --candle-dir "%TRAIN_DIR%" --output "%OUTPUT_JSON%" --trades-csv "%TRADES_CSV%" --point-size 0.01
set "RC=%ERRORLEVEL%"
echo.
echo Registry JSON:
echo %OUTPUT_JSON%
echo Candidate trades CSV:
echo %TRADES_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Exact Stage307 parity did not pass. Review the registry JSON.
pause
exit /b %RC%
