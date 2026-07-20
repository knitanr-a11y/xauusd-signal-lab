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
set "COLLECTOR_DIR=%LOCAL_ROOT%\logs\collector"
set "STATUS_FILE=%COLLECTOR_DIR%\latest_loop_status.json"
set "LOG_FILE=%COLLECTOR_DIR%\collector_forever.log"
set "SCRIPT=%SCRIPT_DIR%run_collect_events_forever.py"
set "ORGANIZED_COLLECTOR=%SCRIPT_DIR%collect_events_once_organized.py"

if not exist "%LOCAL_ENV%" (
  echo [ERROR] Local Cloudflare configuration was not found.
  echo Run this first:
  echo "%SCRIPT_DIR%run_configure_cloudflare.bat"
  echo.
  pause
  exit /b 2
)
if not exist "%ORGANIZED_COLLECTOR%" (
  echo [ERROR] Organized collector wrapper was not found:
  echo "%ORGANIZED_COLLECTOR%"
  echo.
  pause
  exit /b 2
)
if not exist "%COLLECTOR_DIR%" mkdir "%COLLECTOR_DIR%"
if exist "%STOP_FILE%" del /q "%STOP_FILE%" >nul 2>&1

echo ============================================================
echo Mochipoyo Cloudflare collector - AUDIT ONLY FOREVER
echo Poll interval  : 60 seconds
echo Log folder     : %COLLECTOR_DIR%
echo Discord send  : OFF
echo MT5 orders    : OFF
echo Live ready    : OFF
echo Final signal  : OFF
echo Local database: %LOCAL_DB%
echo Stop launcher : %SCRIPT_DIR%stop_collect_events_cloudflare_forever.bat
echo ============================================================
echo.

py -3.12 "%SCRIPT%" ^
  --env "%LOCAL_ENV%" ^
  --db "%LOCAL_DB%" ^
  --interval-seconds 60 ^
  --max-cycles 0 ^
  --limit 500 ^
  --collector-script "%ORGANIZED_COLLECTOR%" ^
  --log "%LOG_FILE%" ^
  --status "%STATUS_FILE%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [STOPPED] Mochipoyo collector loop ended normally.
) else (
  echo [ERROR] Mochipoyo collector loop ended with exit code %EXITCODE%.
)
if exist "%STATUS_FILE%" (
  echo.
  echo -------- LOOP STATUS --------
  type "%STATUS_FILE%"
  echo -------- END STATUS ---------
)
echo.
pause
exit /b %EXITCODE%
