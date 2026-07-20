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
set "LOCK_FILE=%LOCAL_ROOT%\m7c_shadow_loop.lock"
set "RUNTIME_DIR=%LOCAL_ROOT%\m7c_runtime"
set "RUNTIME_MANIFEST=%RUNTIME_DIR%\m7c_prospective_shadow_manifest_runtime.json"
set "M7C_DIR=%LOCAL_ROOT%\logs\m7c"
set "DERIVED_DIR=%LOCAL_ROOT%\logs\derived"
set "RECEIPT=%M7C_DIR%\m7c_runtime_start_receipt.json"
set "TEMPLATE=%SCRIPT_DIR%..\..\config\mochipoyo_alert_research\m7c_prospective_shadow_manifest_v1.json"
set "EPISODE_SCRIPT=%SCRIPT_DIR%build_episodes_once.py"
set "ALIGNMENT_SCRIPT=%SCRIPT_DIR%build_mt5_closed_bar_alignment_once.py"
set "INIT_SCRIPT=%SCRIPT_DIR%initialize_m7c_prospective_shadow_runtime.py"

if exist "%LOCK_FILE%" (
  echo [ERROR] M7C monitor is still running or its lock file remains.
  echo Stop M7C before initializing a new prospective start.
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
if not exist "%LOCAL_DB%" (
  echo [ERROR] Mochipoyo SQLite database was not found.
  echo.
  pause
  exit /b 2
)
if exist "%RUNTIME_MANIFEST%" (
  echo [ERROR] Runtime manifest already exists.
  echo Do not reset an active forward observation.
  echo Existing file: %RUNTIME_MANIFEST%
  echo.
  pause
  exit /b 2
)
if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%"
if not exist "%M7C_DIR%" mkdir "%M7C_DIR%"
if not exist "%DERIVED_DIR%" mkdir "%DERIVED_DIR%"

echo ============================================================
echo Mochipoyo M7C runtime start initialization - AUDIT ONLY
echo Requirement: Cloudflare collector remains running and caught up
echo Requirement: M7C monitor is stopped
echo Runtime file: %RUNTIME_MANIFEST%
echo M7C folder : %M7C_DIR%
echo Derived dir: %DERIVED_DIR%
echo ============================================================
echo.

echo [STEP 1/3] Refreshing M3 episodes...
py -3.12 "%EPISODE_SCRIPT%" --env "%LOCAL_ENV%" --db "%LOCAL_DB%"
if errorlevel 1 goto :failed
if exist "%LOCAL_ROOT%\logs\latest_episode_build_result.json" (
  move /Y "%LOCAL_ROOT%\logs\latest_episode_build_result.json" "%DERIVED_DIR%\latest_episode_build_result.json" >nul
)

echo [STEP 2/3] Refreshing M4 closed-bar alignment...
py -3.12 "%ALIGNMENT_SCRIPT%" ^
  --env "%LOCAL_ENV%" ^
  --db "%LOCAL_DB%" ^
  --output "%DERIVED_DIR%\latest_mt5_closed_bar_alignment_result.json"
if errorlevel 1 goto :failed

echo [STEP 3/3] Freezing a post-catchup prospective start...
py -3.12 "%INIT_SCRIPT%" ^
  --db "%LOCAL_DB%" ^
  --template-manifest "%TEMPLATE%" ^
  --runtime-manifest "%RUNTIME_MANIFEST%" ^
  --receipt "%RECEIPT%" ^
  --lock-file "%LOCK_FILE%" ^
  --required-empty-runs 3
if errorlevel 1 goto :failed

echo.
echo [PASS] M7C runtime start was frozen after collector catch-up.
echo Runtime manifest: %RUNTIME_MANIFEST%
echo Receipt         : %RECEIPT%
echo Next run:
echo "%SCRIPT_DIR%run_build_m7c_prospective_shadow_once.bat"
echo.
pause
exit /b 0

:failed
echo.
echo [FAIL-CLOSED] M7C runtime initialization failed.
echo Keep the collector running, wait for at least three PASS_EMPTY cycles,
echo then run this BAT again. No delivery or execution setting was enabled.
echo.
pause
exit /b 2
