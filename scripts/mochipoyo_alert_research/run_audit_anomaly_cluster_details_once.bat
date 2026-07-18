@echo off
setlocal EnableExtensions DisableDelayedExpansion

if defined LOCALAPPDATA (
  set "LOCAL_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"
) else (
  set "LOCAL_ROOT=%TEMP%\xauusd_signal_lab\mochipoyo_alert_research"
)
set "LOCAL_DB=%LOCAL_ROOT%\mochipoyo_alerts.sqlite3"
set "OUTPUT=%LOCAL_ROOT%\logs\latest_anomaly_cluster_detail_audit.json"
set "SCRIPT_DIR=%~dp0"
set "SCRIPT=%SCRIPT_DIR%audit_anomaly_cluster_details_once.py"

if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo database was not found:
  echo "%LOCAL_DB%"
  pause
  exit /b 2
)

if not exist "%SCRIPT%" (
  echo [ERROR] Audit script was not found:
  echo "%SCRIPT%"
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Stage M3 anomaly cluster detail audit
echo Database access       : READ ONLY
echo Raw alerts modified   : OFF
echo Derived tables changed: OFF
echo Raw JSON displayed    : OFF
echo Secrets displayed     : OFF
echo Discord send          : OFF
echo MT5 orders            : OFF
echo ============================================================
echo.

py -3.12 "%SCRIPT%" --db "%LOCAL_DB%" --output "%OUTPUT%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Anomaly cluster detail audit completed.
  echo Report: "%OUTPUT%"
) else (
  echo [FAIL] Anomaly cluster detail audit failed. Exit code: %EXITCODE%
)
echo.
pause
exit /b %EXITCODE%
