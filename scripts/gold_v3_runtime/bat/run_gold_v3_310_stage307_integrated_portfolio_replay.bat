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
set "LOCATOR_JSON=%TRAIN_DIR%\stage310a_existing_portfolio_locator.json"
set "COMPONENT_JSON=%TRAIN_DIR%\stage310b_component_trade_locator.json"
set "LOCATED_CSV=%TRAIN_DIR%\stage310_existing_portfolio_trades_input.csv"
set "OUTPUT_JSON=%TRAIN_DIR%\stage310_stage307_integrated_portfolio_replay.json"
set "ACCEPTED_CSV=%TRAIN_DIR%\stage310_stage307_integrated_accepted.csv"
set "REJECTED_CSV=%TRAIN_DIR%\stage310_stage307_integrated_rejected.csv"

echo [INFO] Locating the original Stage284/286 trade-level portfolio ledger...
if defined GOLD_V3_EXISTING_PORTFOLIO_CSV (
  %PYTHON_CMD% "%RUNTIME%\gold_v3_310a_existing_portfolio_locator.py" --candle-dir "%TRAIN_DIR%" --output "%LOCATOR_JSON%" --copy-to "%LOCATED_CSV%" --explicit "%GOLD_V3_EXISTING_PORTFOLIO_CSV%"
) else (
  %PYTHON_CMD% "%RUNTIME%\gold_v3_310a_existing_portfolio_locator.py" --candle-dir "%TRAIN_DIR%" --output "%LOCATOR_JSON%" --copy-to "%LOCATED_CSV%"
)
set "LOCATOR_RC=%ERRORLEVEL%"

if not "%LOCATOR_RC%"=="0" (
  echo [INFO] Filename-based locator was inconclusive. Running exact year-count component scan...
  %PYTHON_CMD% "%RUNTIME%\gold_v3_310b_component_trade_locator.py" --candle-dir "%TRAIN_DIR%" --output "%COMPONENT_JSON%" --copy-to "%LOCATED_CSV%"
  set "COMPONENT_RC=!ERRORLEVEL!"
  if not "!COMPONENT_RC!"=="0" (
    echo.
    echo [BLOCKED] The exact Stage284/286 SAFE trade ledger was not recovered.
    echo Filename locator report:
    echo %LOCATOR_JSON%
    echo Structural component report:
    echo %COMPONENT_JSON%
    echo.
    echo Upload stage310b_component_trade_locator.json.
    pause
    exit /b !COMPONENT_RC!
  )
)

echo [INFO] Running Stage310 Stage307 integrated one-position replay...
%PYTHON_CMD% "%RUNTIME%\gold_v3_310_stage307_integrated_portfolio_replay.py" --candle-dir "%TRAIN_DIR%" --existing-portfolio-csv "%LOCATED_CSV%" --output "%OUTPUT_JSON%" --accepted-csv "%ACCEPTED_CSV%" --rejected-csv "%REJECTED_CSV%"
set "RC=%ERRORLEVEL%"
echo.
echo Filename locator JSON:
echo %LOCATOR_JSON%
echo Structural component JSON:
echo %COMPONENT_JSON%
echo Result JSON:
echo %OUTPUT_JSON%
echo Accepted replay CSV:
echo %ACCEPTED_CSV%
echo Rejected overlap CSV:
echo %REJECTED_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage310 could not complete. Review the locator and replay JSON files.
pause
exit /b %RC%
