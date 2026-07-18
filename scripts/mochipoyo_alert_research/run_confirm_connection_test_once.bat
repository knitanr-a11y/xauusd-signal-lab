@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
if defined LOCALAPPDATA (
  set "LOCAL_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"
) else (
  set "LOCAL_ROOT=%TEMP%\xauusd_signal_lab\mochipoyo_alert_research"
)
set "LOCAL_DB=%LOCAL_ROOT%\mochipoyo_alerts.sqlite3"
set "SCRIPT=%SCRIPT_DIR%confirm_connection_test_once.py"

if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo database was not found:
  echo "%LOCAL_DB%"
  echo.
  pause
  exit /b 2
)

if not exist "%SCRIPT%" (
  echo [ERROR] Confirmation script was not found:
  echo "%SCRIPT%"
  echo.
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Stage M3 confirmed connection-test annotation
echo Confirmed episode : XAUUSD:LONG:1
echo Raw alerts         : NOT MODIFIED
echo Episodes           : NOT MODIFIED
echo Annotation table   : WRITE USER CONFIRMATION
echo Clean baseline     : REPORTED SEPARATELY
echo Discord send       : OFF
echo MT5 orders         : OFF
echo Live ready         : OFF
echo Final signal       : OFF
echo ============================================================
echo.

py -3.12 "%SCRIPT%" --db "%LOCAL_DB%" --primary-alert-id 1
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Connection-test annotation and clean baseline completed.
) else (
  echo [FAIL] Connection-test confirmation failed. Exit code: %EXITCODE%
)
echo.
pause
exit /b %EXITCODE%
