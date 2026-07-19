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
set "SCRIPT=%SCRIPT_DIR%build_feature_snapshots_once.py"

if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo SQLite database was not found:
  echo "%LOCAL_DB%"
  echo.
  pause
  exit /b 2
)

if not exist "%SCRIPT%" (
  echo [ERROR] Feature snapshot script was not found:
  echo "%SCRIPT%"
  echo.
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Stage M5 causal feature snapshots - AUDIT ONLY
echo Source bars          : CLOSED ONLY
echo MT5 CSV              : READ ONLY
echo raw_alerts           : NOT MODIFIED
echo episodes             : NOT MODIFIED
echo mt5_alignment        : NOT MODIFIED
echo feature_snapshots    : REBUILT ATOMICALLY
echo Future outcomes      : NOT USED
echo Entry gate           : OFF
echo Private indicator    : NOT RECONSTRUCTED
echo Discord send         : OFF
echo MT5 orders           : OFF
echo Live ready           : OFF
echo Final signal         : OFF
echo ============================================================
echo.

py -3.12 "%SCRIPT%" --env "%LOCAL_ENV%" --db "%LOCAL_DB%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Causal feature snapshot build completed.
) else (
  echo [FAIL] Feature snapshot build failed. Exit code: %EXITCODE%
  echo Previous successful feature snapshots should remain available.
)
echo.
pause
exit /b %EXITCODE%
