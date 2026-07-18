@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
if defined LOCALAPPDATA (
  set "LOCAL_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"
) else (
  set "LOCAL_ROOT=%TEMP%\xauusd_signal_lab\mochipoyo_alert_research"
)
set "LOCAL_DB=%LOCAL_ROOT%\mochipoyo_alerts.sqlite3"
set "SCRIPT=%SCRIPT_DIR%audit_episode_sequences_once.py"

if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo database was not found:
  echo "%LOCAL_DB%"
  echo Run the real Cloudflare collector and Stage M3 episode build first.
  pause
  exit /b 2
)

if not exist "%SCRIPT%" (
  echo [ERROR] Episode audit script was not found:
  echo "%SCRIPT%"
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Stage M3 episode sequence audit - READ ONLY
echo Database write        : OFF
echo Raw alerts modified   : OFF
echo Derived tables changed: OFF
echo Discord send          : OFF
echo MT5 orders            : OFF
echo Future entry fields   : NOT USED
echo ============================================================
echo.

py -3.12 "%SCRIPT%" --db "%LOCAL_DB%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Episode sequence audit completed.
  echo Report: "%LOCAL_ROOT%\logs\latest_episode_sequence_audit.json"
) else (
  echo [FAIL] Episode sequence audit failed. Exit code: %EXITCODE%
)
echo.
pause
exit /b %EXITCODE%
