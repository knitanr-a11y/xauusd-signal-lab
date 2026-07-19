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
set "SCRIPT=%SCRIPT_DIR%build_alert_trigger_signature_audit_once.py"

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
  echo [ERROR] Stage M7A script was not found:
  echo "%SCRIPT%"
  echo.
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Stage M7A alert trigger signature - AUDIT ONLY
echo Positive labels          : GENUINE WEBHOOK / SQLITE EVENTS
echo Negative controls        : VERIFIED M15 OBSERVATION WINDOW ONLY
echo Trigger feature cutoff   : LAST FULLY CLOSED M15 BAR
echo Alert-bar OHLC           : NOT USED
echo Event state              : SEPARATE TRANSITION ELIGIBILITY
echo Exact proprietary clone  : NOT CLAIMED
echo Historical replay        : NOT APPROVED YET
echo Cross-timeframe replay   : NOT APPROVED YET
echo Entry gate               : OFF
echo Rule approval            : OFF
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
  echo [PASS] Stage M7A alert trigger signature audit completed.
) else (
  echo [FAIL] Stage M7A alert trigger signature audit failed. Exit code: %EXITCODE%
  echo Raw alerts, upstream derived stages, and CSV inputs were not modified.
)
echo.
pause
exit /b %EXITCODE%
