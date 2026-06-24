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
set "STAGE313_JSON=%TRAIN_DIR%\stage313_fragility_and_diversification_audit.json"
set "STAGE313_TRADES=%TRAIN_DIR%\stage313_diversified_research_watch_trades.csv"
set "CONTRACT=%TRAIN_DIR%\stage314_mochipoyo_prospective_watch_contract.json"
set "OUTPUT_JSON=%TRAIN_DIR%\stage314_mochipoyo_prospective_watch.json"
set "SIGNALS_CSV=%TRAIN_DIR%\stage314_mochipoyo_prospective_signals.csv"
set "RESOLVED_CSV=%TRAIN_DIR%\stage314_mochipoyo_prospective_resolved.csv"
set "PENDING_CSV=%TRAIN_DIR%\stage314_mochipoyo_prospective_pending.csv"
echo Running Stage314 future-only Mochipoyo prospective watch...
%PYTHON_CMD% "%RUNTIME%\gold_v3_314_prospective_mochipoyo_watch.py" --candle-dir "%TRAIN_DIR%" --stage313-json "%STAGE313_JSON%" --stage313-trades "%STAGE313_TRADES%" --contract "%CONTRACT%" --output "%OUTPUT_JSON%" --signals-csv "%SIGNALS_CSV%" --resolved-csv "%RESOLVED_CSV%" --pending-csv "%PENDING_CSV%" --point-size 0.01
set "RC=%ERRORLEVEL%"
echo.
echo Contract:
echo %CONTRACT%
echo Result:
echo %OUTPUT_JSON%
echo Signals:
echo %SIGNALS_CSV%
echo Resolved:
echo %RESOLVED_CSV%
echo Pending:
echo %PENDING_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage314 did not complete. Review the console message.
pause
exit /b %RC%
