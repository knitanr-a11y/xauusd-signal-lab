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
set "SCRIPT=%SCRIPT_DIR%build_frozen_trigger_kernel_validation_once.py"

if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo SQLite database was not found.
  echo.
  pause
  exit /b 2
)
if not exist "%LOCAL_ENV%" (
  echo [ERROR] Local Mochipoyo .env was not found.
  echo Run run_configure_mt5_csv_root.bat first.
  echo.
  pause
  exit /b 2
)
if not exist "%SCRIPT%" (
  echo [ERROR] Stage M7B one-shot script was not found:
  echo "%SCRIPT%"
  echo.
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Stage M7B frozen trigger kernel - AUDIT ONLY
echo Positive labels          : GENUINE WEBHOOK / SQLITE EVENTS
echo Negative controls        : FROZEN VERIFIED M15 WINDOW ONLY
echo Trigger feature cutoff   : LAST FULLY CLOSED M15 BAR
echo Alert-bar OHLC           : NOT USED
echo M6 outcome metrics       : NOT USED
echo Historical replay        : NOT APPROVED
echo Cross-timeframe replay   : NOT APPROVED
echo Reentry rule freeze      : NOT APPROVED
echo Entry gate               : OFF
echo Discord send             : OFF
echo MT5 orders               : OFF
echo Live ready               : OFF
echo Final signal             : OFF
echo Database                 : %LOCAL_DB%
echo ============================================================
echo.

py -3.12 "%SCRIPT%" --env "%LOCAL_ENV%" --db "%LOCAL_DB%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Stage M7B frozen trigger kernel audit completed.
  echo Output folder: %LOCAL_ROOT%\logs
) else (
  echo [FAIL] Stage M7B frozen trigger kernel audit failed. Exit code: %EXITCODE%
  echo Raw alerts, upstream derived stages, and MT5 CSV inputs were not modified.
)
echo.
pause
exit /b %EXITCODE%
