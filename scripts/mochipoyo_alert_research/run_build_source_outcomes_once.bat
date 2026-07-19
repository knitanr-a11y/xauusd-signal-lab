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
set "SCRIPT=%SCRIPT_DIR%build_source_outcomes_once.py"

if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo SQLite database was not found.
  echo Run the Cloudflare collector first.
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
  echo [ERROR] Stage M6A script was not found:
  echo "%SCRIPT%"
  echo.
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Stage M6A source outcome paths - AUDIT ONLY
echo Primary/reentry entries : SOURCE ALERT CLOSE REFERENCE
echo Exit                    : SOURCE EXIT ALERT
echo MFE/MAE path            : MT5 M1, audited offset
echo Entry minute            : EXCLUDED
echo Exit minute             : EXCLUDED
echo Raw alerts              : NOT MODIFIED
echo Episodes                : NOT MODIFIED
echo MT5 alignment           : NOT MODIFIED
echo Feature snapshots       : NOT MODIFIED
echo Entry gate              : OFF
echo SL/TP policy            : NOT DEFINED YET
echo Actual USD P/L          : NOT DEFINED
echo Discord send            : OFF
echo MT5 orders              : OFF
echo Live ready              : OFF
echo Final signal            : OFF
echo Database                : %LOCAL_DB%
echo ============================================================
echo.

py -3.12 "%SCRIPT%" --env "%LOCAL_ENV%" --db "%LOCAL_DB%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Stage M6A source outcome path build completed.
) else (
  echo [FAIL] Stage M6A source outcome build failed. Exit code: %EXITCODE%
  echo Previous successful derived rows were preserved.
  echo Rerun Stage M3, M4, and M5 first if new alerts were collected.
)
echo.
pause
exit /b %EXITCODE%
