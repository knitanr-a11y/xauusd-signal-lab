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
set "STAGE318_PRIMARY=%TRAIN_DIR%\stage318_primary_high_confidence_trades.csv"
set "STAGE318_PREMIUM=%TRAIN_DIR%\stage318_premium_sparse_watch_trades.csv"
set "CONTRACT=%TRAIN_DIR%\stage319_mochipoyo_dual_tier_prospective_watch_contract.json"
set "OUTPUT_JSON=%TRAIN_DIR%\stage319_mochipoyo_dual_tier_prospective_watch.json"
set "SIGNALS_CSV=%TRAIN_DIR%\stage319_mochipoyo_dual_tier_prospective_signals.csv"
set "RESOLVED_CSV=%TRAIN_DIR%\stage319_mochipoyo_dual_tier_prospective_resolved.csv"
set "PENDING_CSV=%TRAIN_DIR%\stage319_mochipoyo_dual_tier_prospective_pending.csv"
echo Running Stage319 Mochipoyo dual-tier prospective watch...
%PYTHON_CMD% "%RUNTIME%\gold_v3_319_mochipoyo_dual_tier_prospective_watch.py" --candle-dir "%TRAIN_DIR%" --stage318-json "%STAGE318_JSON%" --stage318-primary "%STAGE318_PRIMARY%" --stage318-premium "%STAGE318_PREMIUM%" --contract "%CONTRACT%" --output "%OUTPUT_JSON%" --signals-csv "%SIGNALS_CSV%" --resolved-csv "%RESOLVED_CSV%" --pending-csv "%PENDING_CSV%" --point-size 0.01
set "RC=%ERRORLEVEL%"
echo.
echo Frozen contract:
echo %CONTRACT%
echo Result JSON:
echo %OUTPUT_JSON%
echo Signals:
echo %SIGNALS_CSV%
echo Resolved:
echo %RESOLVED_CSV%
echo Pending:
echo %PENDING_CSV%
echo.
if not "%RC%"=="0" echo [BLOCKED] Stage319 did not complete. Review the console message.
pause
exit /b %RC%
