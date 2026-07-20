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
set "M7C_DIR=%LOCAL_ROOT%\logs\m7c"
set "DERIVED_DIR=%LOCAL_ROOT%\logs\derived"
set "SCRIPT=%SCRIPT_DIR%build_m7c_prospective_shadow_once.py"

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
  echo [ERROR] Stage M7C one-shot script was not found:
  echo "%SCRIPT%"
  echo.
  pause
  exit /b 2
)
if not exist "%M7C_DIR%" mkdir "%M7C_DIR%"
if not exist "%DERIVED_DIR%" mkdir "%DERIVED_DIR%"

echo ============================================================
echo Mochipoyo Stage M7C prospective shadow - AUDIT ONLY
echo Runtime manifest          : %RUNTIME_MANIFEST%
echo M7C output folder         : %M7C_DIR%
echo Derived audit folder      : %DERIVED_DIR%
echo Formula refit             : OFF
echo Historical replay         : OFF
echo Reentry rule              : NOT USED
echo Entry gate                : OFF
echo Discord send              : OFF
echo MT5 orders                : OFF
echo Live ready                : OFF
echo Final signal              : OFF
echo ============================================================
echo.

py -3.12 "%SCRIPT%" ^
  --env "%LOCAL_ENV%" ^
  --db "%LOCAL_DB%" ^
  --manifest "%RUNTIME_MANIFEST%" ^
  --output-dir "%M7C_DIR%" ^
  --derived-output-dir "%DERIVED_DIR%" ^
  --refresh-upstream-if-stale
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Stage M7C prospective shadow audit cycle completed.
  echo Output folder: %M7C_DIR%
) else (
  echo [FAIL-CLOSED] Stage M7C cycle failed. Exit code: %EXITCODE%
  echo Frozen formulas, raw alerts, MT5 CSV inputs, delivery, and execution settings were not changed.
)
echo.
pause
exit /b %EXITCODE%
