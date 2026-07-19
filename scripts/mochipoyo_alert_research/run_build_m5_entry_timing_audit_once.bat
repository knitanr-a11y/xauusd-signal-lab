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
set "SCRIPT=%SCRIPT_DIR%build_m5_entry_timing_audit_once.py"

if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo SQLite database was not found.
  echo Run the collector and upstream stages first.
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
  echo [ERROR] Stage M6C script was not found:
  echo "%SCRIPT%"
  echo.
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Stage M6C M5 entry timing audit - AUDIT ONLY
echo Source events            : WEBHOOK / SQLITE IDS
echo Chart label redraw       : NOT REQUIRED
echo Candidate detection      : CLOSED M5 BARS ONLY
echo Outcome used for trigger : NO
echo Variant price basis      : MT5 ONLY
echo Entry gate               : OFF
echo Rule approval            : OFF
echo Discord send             : OFF
echo MT5 orders               : OFF
echo Live ready               : OFF
echo Final signal             : OFF
echo Database                 : %LOCAL_DB%
echo ============================================================
echo.

py -3.12 "%SCRIPT%" --env "%LOCAL_ENV%" --db "%LOCAL_DB%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Stage M6C M5 entry timing audit completed.
) else (
  echo [FAIL] Stage M6C M5 entry timing audit failed. Exit code: %EXITCODE%
  echo Previous successful derived rows were preserved.
  echo Rerun M3, M4, M5, M6A, and M6B first if new alerts were collected.
)
echo.
pause
exit /b %EXITCODE%
