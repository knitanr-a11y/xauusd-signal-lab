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
set "CONFIRM_SCRIPT=%SCRIPT_DIR%confirm_connection_test_alert_once.py"
set "BUILD_SCRIPT=%SCRIPT_DIR%build_episodes_once.py"

if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo SQLite database was not found.
  echo "%LOCAL_DB%"
  echo.
  pause
  exit /b 2
)

if not exist "%CONFIRM_SCRIPT%" (
  echo [ERROR] Confirmation script was not found.
  pause
  exit /b 2
)

if not exist "%BUILD_SCRIPT%" (
  echo [ERROR] Episode builder was not found.
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Stage M3 - CONFIRM ID1 TEST AND REBUILD
echo Confirmed test row : ID 1 only
echo IDs 4,6,7,9       : NORMAL ALERTS
echo Raw alerts         : NOT MODIFIED
echo Annotation         : ID1 CONNECTION_TEST
echo Derived episodes   : REBUILT ATOMICALLY
echo Discord send       : OFF
echo MT5 orders         : OFF
echo Live ready         : OFF
echo Final signal       : OFF
echo ============================================================
echo.

py -3.12 "%CONFIRM_SCRIPT%" --env "%LOCAL_ENV%" --db "%LOCAL_DB%" --raw-alert-id 1
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
  echo.
  echo [FAIL] ID1 confirmation failed. Episode rebuild was not run.
  pause
  exit /b %EXITCODE%
)

echo.
echo [STEP 2] Rebuilding clean episodes with ID1 excluded...
py -3.12 "%BUILD_SCRIPT%" --env "%LOCAL_ENV%" --db "%LOCAL_DB%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] ID1 was annotated and clean episodes were rebuilt.
) else (
  echo [FAIL] ID1 annotation succeeded, but episode rebuild failed.
  echo Raw alerts were not modified. Re-run the episode builder after review.
)
echo.
pause
exit /b %EXITCODE%
