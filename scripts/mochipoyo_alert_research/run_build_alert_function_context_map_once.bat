@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
if defined LOCALAPPDATA (
  set "LOCAL_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"
) else (
  set "LOCAL_ROOT=%TEMP%\xauusd_signal_lab\mochipoyo_alert_research"
)
set "LOCAL_DB=%LOCAL_ROOT%\mochipoyo_alerts.sqlite3"
set "SCRIPT=%SCRIPT_DIR%build_alert_function_context_map_once.py"

if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo SQLite database was not found.
  echo Run the Cloudflare collector and Stages M3-M6A first.
  echo.
  pause
  exit /b 2
)

if not exist "%SCRIPT%" (
  echo [ERROR] Stage M6B script was not found:
  echo "%SCRIPT%"
  echo.
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Stage M6B alert function context map - AUDIT ONLY
echo Entry context source    : CLOSED-BAR M5/M15/H1/H4/D1 FEATURES
echo Result source           : STAGE M6A DESCRIPTIVE OUTCOMES
echo A/B/C classification    : ENTRY-TIME INFORMATION ONLY
echo Outcome used for class  : NO
echo Reentry identity        : WEBHOOK / SQLITE SOURCE EVENT ID
echo Chart label redraw      : NOT REQUIRED
echo Current sample tuning   : OFF
echo Entry gate              : OFF
echo Automatic rule approval : OFF
echo Discord send            : OFF
echo MT5 orders              : OFF
echo Live ready              : OFF
echo Final signal            : OFF
echo Database                : %LOCAL_DB%
echo ============================================================
echo.

py -3.12 "%SCRIPT%" --db "%LOCAL_DB%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Stage M6B alert function context map completed.
) else (
  echo [FAIL] Stage M6B context map failed. Exit code: %EXITCODE%
  echo Previous successful M6B rows were preserved.
  echo Rerun Stages M3, M4, M5, and M6A first if new alerts were collected.
)
echo.
pause
exit /b %EXITCODE%
