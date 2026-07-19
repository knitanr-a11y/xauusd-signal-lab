@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
if defined LOCALAPPDATA (
  set "LOCAL_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"
) else (
  set "LOCAL_ROOT=%TEMP%\xauusd_signal_lab\mochipoyo_alert_research"
)
set "LOCAL_ENV=%LOCAL_ROOT%\.env"
set "LOCAL_DB=%LOCAL_ROOT%\mochipoyo_alerts.sqlite3"
set "SCRIPT=%SCRIPT_DIR%build_mt5_closed_bar_alignment_once.py"

if not exist "%LOCAL_ENV%" (
  echo [ERROR] Local Mochipoyo configuration was not found.
  echo Run these first:
  echo "%SCRIPT_DIR%run_configure_cloudflare.bat"
  echo "%SCRIPT_DIR%run_configure_mt5_csv_root.bat"
  echo.
  pause
  exit /b 2
)

if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo SQLite database was not found.
  echo Run the Cloudflare collector first.
  echo.
  pause
  exit /b 2
)

if not exist "%SCRIPT%" (
  echo [ERROR] Alignment script was not found:
  echo "%SCRIPT%"
  echo.
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Stage M4 MT5 closed-bar alignment - AUDIT ONLY
echo MT5 CSV files : READ ONLY
echo Raw alerts    : READ ONLY
echo Episodes      : READ ONLY
echo Alignment     : DERIVED TABLE REBUILT ATOMICALLY
echo Offset        : INFERRED FROM M1, NOT HARDCODED
echo H4 / D1 join  : CLOSED UTC INTERVAL AS-OF
echo Discord send : OFF
echo MT5 orders   : OFF
echo Live ready   : OFF
echo Final signal : OFF
echo ============================================================
echo.

py -3.12 "%SCRIPT%" --env "%LOCAL_ENV%" --db "%LOCAL_DB%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] MT5 closed-bar alignment completed.
) else (
  echo [FAIL] MT5 closed-bar alignment failed. Exit code: %EXITCODE%
  echo Previous successful derived alignment, raw alerts, and CSV files were preserved.
)
echo.
pause
exit /b %EXITCODE%
