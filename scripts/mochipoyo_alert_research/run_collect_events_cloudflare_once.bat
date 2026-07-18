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
set "ERROR_JSON=%LOCAL_ROOT%\logs\latest_collection_error.json"
set "RESULT_JSON=%LOCAL_ROOT%\logs\latest_collection_result.json"

if not exist "%LOCAL_ENV%" (
  echo [ERROR] Local Cloudflare configuration was not found.
  echo Run this first:
  echo "%SCRIPT_DIR%run_configure_cloudflare.bat"
  echo.
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Cloudflare collection - ONE SHOT READ ONLY
echo Permanent loop : OFF
echo Discord send   : OFF
echo MT5 orders     : OFF
echo Live ready     : OFF
echo Final signal   : OFF
echo Local database : %LOCAL_DB%
echo ============================================================
echo.

call "%SCRIPT_DIR%run_collect_events_once.bat" --env "%LOCAL_ENV%" --db "%LOCAL_DB%" --limit 500
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] One-shot Cloudflare collection completed.
  echo No permanent loop was started.
  echo Local database: "%LOCAL_DB%"
  if exist "%RESULT_JSON%" (
    echo Diagnostic result: "%RESULT_JSON%"
  )
  echo.
  pause
) else (
  echo [FAIL] One-shot Cloudflare collection failed. Exit code: %EXITCODE%
  echo No cursor was advanced.
  if exist "%ERROR_JSON%" (
    echo.
    echo -------- REDACTED DIAGNOSTIC --------
    type "%ERROR_JSON%"
    echo -------- END DIAGNOSTIC ------------
  ) else (
    echo Redacted diagnostic file was not created.
  )
  echo.
  pause
)

exit /b %EXITCODE%
