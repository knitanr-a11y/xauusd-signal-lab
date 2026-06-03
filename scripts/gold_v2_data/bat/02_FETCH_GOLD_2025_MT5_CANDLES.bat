@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
for %%I in ("%REPO_ROOT%\..\..") do set "FILES_DIR=%%~fI"

set "SCRIPT=%REPO_ROOT%\scripts\gold_v2_data\fetch_mt5_candles.py"
set "OUTDIR=%FILES_DIR%\FX_OUTPUTS\mt5_candles\gold_2025"

rem Change SYMBOL if your broker uses a different name.
rem The Python script also tries common aliases and fuzzy XAU/GOLD search.
set "SYMBOL=XAUUSD"
set "START=2025-01-01"
set "END=2026-01-01"
set "TIMEFRAMES=M1,M5,M15,H1,H4,D1"

echo [GOLD V2 MT5 DATA] Fetch GOLD candles from MT5
echo REPO_ROOT=%REPO_ROOT%
echo OUTDIR=%OUTDIR%
echo SYMBOL=%SYMBOL%
echo PERIOD=%START% to %END%
echo TIMEFRAMES=%TIMEFRAMES%
echo.

if not exist "%SCRIPT%" (
  echo [ERROR] Script not found: %SCRIPT%
  pause
  exit /b 1
)

python "%SCRIPT%" ^
  --symbol "%SYMBOL%" ^
  --start "%START%" ^
  --end "%END%" ^
  --timeframes "%TIMEFRAMES%" ^
  --output-dir "%OUTDIR%" ^
  --sep ";"

set "RC=%ERRORLEVEL%"
echo.
echo [GOLD V2 MT5 DATA] Finished with exit code %RC%
echo Output dir: %OUTDIR%
echo.
echo If rows are unexpectedly low, open MT5 and increase:
echo Tools ^> Options ^> Charts ^> Max bars in chart
pause
exit /b %RC%
