@echo off
setlocal EnableExtensions EnableDelayedExpansion

for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if not exist "config\mochipoyo_alert_research\current_state_20260728.json" (
  echo ============================================================
  echo [STOP] Repository root could not be resolved from this BAT.
  echo ============================================================
  echo BAT:  %~f0
  echo ROOT: %REPO_ROOT%
  echo No STOP request was sent. Do not force-close loops or delete locks.
  pause
  exit /b 2
)

set "OPERATOR=scripts\mochipoyo_alert_research\recovery\python\stop_bounded_adapter_loops_for_v4_upgrade.py"

echo ============================================================
echo MOCHIPOYO - GRACEFUL STOP FOR V4 PRIVATE SNAPSHOT UPGRADE
echo ============================================================
echo.
echo Repository root: %CD%
echo This requests normal STOP-file shutdown for M9V/M9Y/M10B/M10E/M10P/M10P2/M10W19.
echo It does NOT stop collector, M7C, M8C, MT5, or other loops.
echo It does NOT kill processes, delete locks, edit runtimes, or reset starts.
echo.

if exist "%OPERATOR%" goto :python_operator

echo [NOTICE] Standalone stop operator is unavailable in this checkout.
echo Using the embedded lock-preserving STOP-file fallback.
echo.

goto :embedded_stop

:python_operator
python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%OPERATOR%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [STOP] V4 upgrade stop operator syntax preflight failed.
  echo No STOP request was sent. Do not close loops forcibly or delete locks.
  pause
  exit /b 2
)
python "%OPERATOR%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP BLOCKED] Leave all evidence unchanged and send this screen to ChatGPT.
  pause
  exit /b %RC%
)
echo [STOP PASS] All seven bounded-adapter loops are stopped naturally.
echo Fetch/Pull latest branch, then restart the seven BAT03 launchers in order.
pause
exit /b 0

:embedded_stop
if "%LOCALAPPDATA%"=="" (
  echo [STOP] LOCALAPPDATA is unavailable. No STOP request was sent.
  pause
  exit /b 2
)
set "LOCAL_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"

if not exist "%LOCAL_ROOT%\m9v_runtime" goto :runtime_missing
if not exist "%LOCAL_ROOT%\m9y_runtime" goto :runtime_missing
if not exist "%LOCAL_ROOT%\m10b_runtime" goto :runtime_missing
if not exist "%LOCAL_ROOT%\m10e_runtime" goto :runtime_missing
if not exist "%LOCAL_ROOT%\m10p_runtime" goto :runtime_missing
if not exist "%LOCAL_ROOT%\m10p2_runtime" goto :runtime_missing
if not exist "%LOCAL_ROOT%\m10w19_runtime" goto :runtime_missing

>"%LOCAL_ROOT%\m9v_runtime\STOP_M9V_SHADOW_LOOP" echo V4_PRIVATE_SNAPSHOT_UPGRADE_STOP_REQUEST
>"%LOCAL_ROOT%\m9y_runtime\STOP_M9Y_SHADOW_LOOP" echo V4_PRIVATE_SNAPSHOT_UPGRADE_STOP_REQUEST
>"%LOCAL_ROOT%\m10b_runtime\STOP_M10B_SHADOW_LOOP" echo V4_PRIVATE_SNAPSHOT_UPGRADE_STOP_REQUEST
>"%LOCAL_ROOT%\m10e_runtime\STOP_M10E_SHADOW_LOOP" echo V4_PRIVATE_SNAPSHOT_UPGRADE_STOP_REQUEST
>"%LOCAL_ROOT%\m10p_runtime\STOP_M10P_SHADOW_LOOP" echo V4_PRIVATE_SNAPSHOT_UPGRADE_STOP_REQUEST
>"%LOCAL_ROOT%\m10p2_runtime\STOP_M10P2_SHADOW_LOOP" echo V4_PRIVATE_SNAPSHOT_UPGRADE_STOP_REQUEST
>"%LOCAL_ROOT%\m10w19_runtime\STOP_M10W19_SHADOW_LOOP" echo V4_PRIVATE_SNAPSHOT_UPGRADE_STOP_REQUEST

echo [STOP REQUESTED] Waiting for existing runners to remove their own locks...
set /a WAITED=0

:wait_for_locks
set "ANY_LOCK="
if exist "%LOCAL_ROOT%\m9v_runtime\m9v_shadow_loop.lock" set "ANY_LOCK=1"
if exist "%LOCAL_ROOT%\m9y_runtime\m9y_shadow_loop.lock" set "ANY_LOCK=1"
if exist "%LOCAL_ROOT%\m10b_runtime\m10b_shadow_loop.lock" set "ANY_LOCK=1"
if exist "%LOCAL_ROOT%\m10e_runtime\m10e_shadow_loop.lock" set "ANY_LOCK=1"
if exist "%LOCAL_ROOT%\m10p_runtime\m10p_shadow_loop.lock" set "ANY_LOCK=1"
if exist "%LOCAL_ROOT%\m10p2_runtime\m10p2_shadow_loop.lock" set "ANY_LOCK=1"
if exist "%LOCAL_ROOT%\m10w19_runtime\m10w19_shadow_loop.lock" set "ANY_LOCK=1"

if not defined ANY_LOCK goto :embedded_pass
if !WAITED! GEQ 180 goto :embedded_timeout
timeout /t 1 /nobreak >nul
set /a WAITED+=1
goto :wait_for_locks

:embedded_pass
timeout /t 2 /nobreak >nul
echo [STOP PASS] All seven bounded-adapter loop locks disappeared naturally.
echo No process was killed and no lock was deleted by this BAT.
echo Fetch/Pull latest branch, then restart the seven BAT03 launchers in order.
pause
exit /b 0

:embedded_timeout
echo [STOP BLOCKED] One or more loop locks remain after 180 seconds.
echo Do not taskkill processes or delete locks. Send this screen to ChatGPT.
pause
exit /b 3

:runtime_missing
echo [STOP] One or more protected runtime directories are missing.
echo No STOP request was sent. Do not initialize, reset, or delete anything.
pause
exit /b 2
