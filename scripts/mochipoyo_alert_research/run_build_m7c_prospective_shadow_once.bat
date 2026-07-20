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
set "SCRIPT=%SCRIPT_DIR%build_m7c_prospective_shadow_once.py"

if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo SQLite database was not found.
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
  echo [ERROR] Stage M7C one-shot script was not found:
  echo "%SCRIPT%"
  echo.
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Stage M7C prospective shadow - AUDIT ONLY
echo Forward start            : FROZEN AFTER M7B PASS
echo Formula refit            : OFF
echo Historical replay        : OFF
echo Cross-timeframe replay   : OFF
echo Reentry rule             : NOT USED
echo Upstream stale handling  : M3/M4 DERIVED TABLE REFRESH ONLY
echo Entry gate               : OFF
echo Discord send             : OFF
echo MT5 orders               : OFF
echo Live ready               : OFF
echo Final signal             : OFF
echo Database                 : %LOCAL_DB%
echo ============================================================
echo.

py -3.12 "%SCRIPT%" ^
  --env "%LOCAL_ENV%" ^
  --db "%LOCAL_DB%" ^
  --refresh-upstream-if-stale
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Stage M7C prospective shadow audit cycle completed.
  echo Output folder: %LOCAL_ROOT%\logs
) else (
  echo [FAIL-CLOSED] Stage M7C cycle failed. Exit code: %EXITCODE%
  echo Frozen formulas, raw alerts, MT5 CSV inputs, delivery, and execution settings were not changed.
)
echo.
pause
exit /b %EXITCODE%
