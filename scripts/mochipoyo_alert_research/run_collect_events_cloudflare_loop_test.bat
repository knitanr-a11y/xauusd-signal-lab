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
set "STOP_FILE=%LOCAL_ROOT%\STOP_COLLECTOR_LOOP"
set "SCRIPT=%SCRIPT_DIR%run_collect_events_forever.py"

if not exist "%LOCAL_ENV%" (
  echo [ERROR] Local Cloudflare configuration was not found.
  echo Run this first:
  echo "%SCRIPT_DIR%run_configure_cloudflare.bat"
  echo.
  pause
  exit /b 2
)

if exist "%STOP_FILE%" del /q "%STOP_FILE%" >nul 2>&1

echo ============================================================
echo Mochipoyo collector loop TEST - READ ONLY
echo Cycles        : 3
echo Interval      : 10 seconds
echo Permanent loop: OFF
echo Discord send  : OFF
echo MT5 orders    : OFF
echo Live ready    : OFF
echo Final signal  : OFF
echo ============================================================
echo.

py -3.12 "%SCRIPT%" ^
  --env "%LOCAL_ENV%" ^
  --db "%LOCAL_DB%" ^
  --interval-seconds 10 ^
  --max-cycles 3 ^
  --limit 500
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Three-cycle collector loop test completed.
) else (
  echo [FAIL] Collector loop test failed. Exit code: %EXITCODE%
)
echo.
pause
exit /b %EXITCODE%
