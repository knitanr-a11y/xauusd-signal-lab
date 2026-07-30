@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if defined LOCALAPPDATA (
  set "LOCAL_ROOT=%LOCALAPPDATA%\xauusd_signal_lab"
) else (
  set "LOCAL_ROOT=%TEMP%\xauusd_signal_lab"
)

set "EXPECTED_DATA_PATH=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675"
set "CSV_PATH=%EXPECTED_DATA_PATH%\MQL5\Files\btcusdsharp_m15.csv"
set "FROZEN_CSV_SHA256=b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148"
set "EXPECTED_SYMBOL=BTCUSD#"
set "OUTPUT_ROOT=%LOCAL_ROOT%\btc_ml_v1\outputs\BCR08_mt5_symbol_cost_provenance"
set "LATEST_ZIP=%OUTPUT_ROOT%\LATEST\99_UPLOAD_PACKAGE.zip"
set "SCRIPT=scripts\btc_ml_v1\BCR08_mt5_symbol_cost_provenance\python\run_bcr08_mt5_symbol_cost_provenance.py"

set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  echo [BCR08] FAILED: Python was not found.
  pause
  exit /b 9009
)

if not exist "%SCRIPT%" (
  echo [BCR08] FAILED: Script was not found.
  echo %SCRIPT%
  pause
  exit /b 2
)

if not exist "%CSV_PATH%" (
  echo [BCR08] FAILED: BTC M15 CSV was not found at the frozen path.
  echo %CSV_PATH%
  echo MT5, Collector and M7C were not changed.
  pause
  exit /b 2
)

echo ============================================================
echo BCR08 - MT5 SYMBOL AND COST PROVENANCE
echo ============================================================
echo Expected data path : %EXPECTED_DATA_PATH%
echo BTC M15 CSV        : %CSV_PATH%
echo Expected symbol    : %EXPECTED_SYMBOL%
echo Output root        : %OUTPUT_ROOT%
echo MT5 requirement    : terminal64.exe must ALREADY be running
echo MT5 actions        : READ-ONLY metadata calls only
echo Orders/history     : NOT QUERIED, NOT SENT
echo Account export     : login/name/balance/equity/profit REDACTED
echo Collector/M7C      : KEEP RUNNING, NO CHANGE
echo GOLD/MOCHIPOYO     : NO CHANGE
echo PnL evaluation     : NOT PERFORMED
echo ============================================================
echo.

%PYTHON_CMD% "%SCRIPT%" ^
  --output-root "%OUTPUT_ROOT%" ^
  --expected-data-path "%EXPECTED_DATA_PATH%" ^
  --expected-symbol "%EXPECTED_SYMBOL%" ^
  --csv-path "%CSV_PATH%" ^
  --frozen-csv-sha256 "%FROZEN_CSV_SHA256%"
set "EXIT_CODE=%ERRORLEVEL%"

if exist "%LATEST_ZIP%" (
  start "" explorer.exe /select,"%LATEST_ZIP%"
) else if exist "%OUTPUT_ROOT%\LATEST" (
  start "" explorer.exe "%OUTPUT_ROOT%\LATEST"
)

echo.
echo [BCR08] exit_code=%EXIT_CODE%
if "%EXIT_CODE%"=="0" (
  echo [BCR08] Evidence package completed. Upload the selected ZIP and stop.
) else (
  echo [BCR08] Evidence collection was blocked or failed.
  echo [BCR08] Upload the first ZIP if one was created and do not rerun automatically.
)
pause
exit /b %EXIT_CODE%
