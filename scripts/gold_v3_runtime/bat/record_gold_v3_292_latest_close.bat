@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\..\..\.."
set "RUNTIME=%CD%\scripts\gold_v3_runtime"
set "FILES_DIR="
for /d %%D in ("%APPDATA%\MetaQuotes\Terminal\*") do (
  if not defined FILES_DIR (
    set "CANDIDATE=%%~fD\MQL5\Files"
    if exist "!CANDIDATE!\FX_OUTPUTS\gold_v3\292_safe_portfolio_live\gold_v3_292_live_signal_ledger.csv" set "FILES_DIR=!CANDIDATE!"
  )
)
if not defined FILES_DIR (echo [BLOCKED] Stage292 ledger was not found.& pause& exit /b 2)
set /p PRICE=Actual close price: 
set /p PNL=Actual realized PnL: 
set /p REASON=Close reason ^(TP/SL/TIME/MANUAL^): 
python "%RUNTIME%\gold_v3_292_record_execution.py" --candle-dir "%FILES_DIR%" --event-type CLOSED --price %PRICE% --pnl %PNL% --reason %REASON%
if errorlevel 1 (echo [BLOCKED] Close was not recorded.) else (echo Close recorded.)
pause
