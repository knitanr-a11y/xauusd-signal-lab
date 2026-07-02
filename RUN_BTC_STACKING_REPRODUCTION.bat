@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage

set "HISTORY_DIR=%~1"
set "H4_WARMUP_CSV=%~2"
set "OUTPUT_DIR=%~3"
if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=outputs\btc_ml_v1\btc_stacking_reproduction_20260702"

python scripts\btc_ml_v1\research\reproduce_btc_stacking_portfolio.py ^
  --history-dir "%HISTORY_DIR%" ^
  --h4-warmup-csv "%H4_WARMUP_CSV%" ^
  --output-dir "%OUTPUT_DIR%"
exit /b %ERRORLEVEL%

:usage
echo Usage:
echo   RUN_BTC_STACKING_REPRODUCTION.bat "HISTORY_DIR" "H4_WARMUP_CSV" ["OUTPUT_DIR"]
echo.
echo HISTORY_DIR must contain:
echo   btcusdsharp_m5.csv
  echo   btcusdsharp_m15.csv
  echo   btcusdsharp_h1.csv
  echo   btcusdsharp_d1.csv
exit /b 2
