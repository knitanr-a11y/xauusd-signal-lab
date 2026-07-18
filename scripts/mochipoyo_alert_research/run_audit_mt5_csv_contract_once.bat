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
set "OUTPUT=%LOCAL_ROOT%\logs\latest_mt5_csv_contract_audit.json"
echo ============================================================
echo Mochipoyo Stage M4 MT5 CSV contract audit - READ ONLY
 echo CSV files     : READ ONLY
 echo Database      : READ ONLY
 echo Offset        : INFERRED, NOT HARDCODED
 echo H4/D1 matching: AS-OF CLOSED INTERVAL
 echo Discord send  : OFF
 echo MT5 orders    : OFF
 echo ============================================================
echo.
py -3.12 "%SCRIPT_DIR%audit_mt5_csv_contract_once.py" --env "%LOCAL_ENV%" --db "%LOCAL_DB%" --output "%OUTPUT%"
set "EXITCODE=%ERRORLEVEL%"
echo.
if "%EXITCODE%"=="0" (
  echo [PASS] MT5 CSV contract audit completed.
) else (
  echo [FAIL] MT5 CSV contract audit failed. Exit code: %EXITCODE%
)
echo Report: "%OUTPUT%"
echo.
pause
exit /b %EXITCODE%
