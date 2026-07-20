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
set "RUNTIME_MANIFEST=%LOCAL_ROOT%\m7c_runtime\m7c_prospective_shadow_manifest_runtime.json"
set "STOP_FILE=%LOCAL_ROOT%\STOP_M7C_SHADOW_LOOP"
set "M7C_DIR=%LOCAL_ROOT%\logs\m7c"
set "DERIVED_DIR=%LOCAL_ROOT%\logs\derived"
set "STATUS_FILE=%M7C_DIR%\latest_m7c_shadow_loop_status.json"
set "LOG_FILE=%M7C_DIR%\m7c_shadow_forever.log"
set "SCRIPT=%SCRIPT_DIR%run_m7c_prospective_shadow_forever_safe.py"

if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo SQLite database was not found.
  echo.
  pause
  exit /b 2
)
if not exist "%LOCAL_ENV%" (
  echo [ERROR] Local Mochipoyo .env was not found.
  echo.
  pause
  exit /b 2
)
if not exist "%RUNTIME_MANIFEST%" (
  echo [ERROR] Local M7C runtime manifest was not found.
  echo Run this first:
  echo "%SCRIPT_DIR%run_initialize_m7c_prospective_shadow_runtime_once.bat"
  echo.
  pause
  exit /b 2
)
if not exist "%SCRIPT%" (
  echo [ERROR] Stage M7C safe loop script was not found:
  echo "%SCRIPT%"
  echo.
  pause
  exit /b 2
)
if not exist "%M7C_DIR%" mkdir "%M7C_DIR%"
if not exist "%DERIVED_DIR%" mkdir "%DERIVED_DIR%"
if exist "%STOP_FILE%" del /q "%STOP_FILE%" >nul 2>&1

echo ============================================================
echo Mochipoyo Stage M7C prospective shadow - AUDIT ONLY FOREVER
echo Poll interval            : 300 seconds
echo Runtime manifest         : %RUNTIME_MANIFEST%
echo M7C folder               : %M7C_DIR%
echo Derived folder           : %DERIVED_DIR%
echo Existing collector       : MUST REMAIN RUNNING SEPARATELY
echo Contract exit 2          : STOP INSTEAD OF REPEATING
echo Formula refit            : OFF
echo Historical replay        : OFF
echo Reentry rule             : NOT USED
echo Entry gate               : OFF
echo Discord send             : OFF
echo MT5 orders               : OFF
echo Live ready               : OFF
echo Final signal             : OFF
echo Stop launcher            : %SCRIPT_DIR%stop_m7c_prospective_shadow_forever.bat
echo ============================================================
echo.

py -3.12 "%SCRIPT%" ^
  --env "%LOCAL_ENV%" ^
  --db "%LOCAL_DB%" ^
  --manifest "%RUNTIME_MANIFEST%" ^
  --output-dir "%M7C_DIR%" ^
  --derived-output-dir "%DERIVED_DIR%" ^
  --interval-seconds 300 ^
  --max-cycles 0 ^
  --log "%LOG_FILE%" ^
  --status "%STATUS_FILE%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [STOPPED] M7C shadow loop ended normally.
) else (
  echo [ERROR] M7C shadow loop ended with exit code %EXITCODE%.
)
if exist "%STATUS_FILE%" (
  echo.
  echo -------- M7C LOOP STATUS --------
  type "%STATUS_FILE%"
  echo -------- END STATUS -------------
)
echo.
pause
exit /b %EXITCODE%
