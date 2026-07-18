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
set "SCRIPT=%SCRIPT_DIR%build_episodes_once.py"

if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo SQLite database was not found.
  echo Run the Cloudflare collector first:
  echo "%SCRIPT_DIR%run_collect_events_cloudflare_once.bat"
  echo.
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Stage M3 episode build - AUDIT ONLY
echo Raw alerts    : READ ONLY
echo Derived tables: REBUILT ATOMICALLY
echo Discord send : OFF
echo MT5 orders   : OFF
echo Live ready   : OFF
echo Final signal : OFF
echo Database     : %LOCAL_DB%
echo ============================================================
echo.

py -3.12 "%SCRIPT%" --env "%LOCAL_ENV%" --db "%LOCAL_DB%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Episode build completed.
) else (
  echo [FAIL] Episode build failed. Exit code: %EXITCODE%
  echo Existing raw alerts and the previous successful derived tables were preserved.
)
echo.
pause
exit /b %EXITCODE%
