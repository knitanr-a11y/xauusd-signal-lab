@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
set "RUN_ONCE=%SCRIPT_DIR%run_live_once.bat"
set "ROTATE_LOG=%SCRIPT_DIR%rotate_live_loop_log.bat"
set "STOP_FILE=%SCRIPT_DIR%STOP_LIVE_LOOP"
set "LOCK_DIR=%SCRIPT_DIR%live_loop.lock"
set "OUTPUT_DIR=%REPO_ROOT%\outputs\gold_ml_v1\live_research_challenger"
set "LOOP_LOG=%OUTPUT_DIR%\live_loop.log"

if not defined GML1_LIVE_INTERVAL_SECONDS set "GML1_LIVE_INTERVAL_SECONDS=60"

if not exist "%RUN_ONCE%" (
  echo ERROR: run_live_once.bat was not found.
  echo Expected: "%RUN_ONCE%"
  echo.
  pause
  exit /b 2
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%" >nul 2>&1
if errorlevel 1 (
  echo ERROR: could not create output directory.
  echo "%OUTPUT_DIR%"
  echo.
  pause
  exit /b 2
)

mkdir "%LOCK_DIR%" >nul 2>&1
if errorlevel 1 (
  echo ERROR: another live loop may already be running, or a stale lock remains.
  echo Lock: "%LOCK_DIR%"
  echo Stop the existing loop with stop_live_loop.bat.
  echo If no loop is running, use reset_live_loop_lock.bat.
  echo.
  pause
  exit /b 3
)

if exist "%STOP_FILE%" del /q "%STOP_FILE%" >nul 2>&1
if exist "%ROTATE_LOG%" call "%ROTATE_LOG%" "%OUTPUT_DIR%"

>>"%LOOP_LOG%" echo [%date% %time%] LOOP_START interval_seconds=%GML1_LIVE_INTERVAL_SECONDS%
echo ============================================================
echo GML1 live research challenger loop
echo ============================================================
echo Interval : %GML1_LIVE_INTERVAL_SECONDS% seconds
echo Output   : %OUTPUT_DIR%
echo Log      : %LOOP_LOG%
echo Stop     : run stop_live_loop.bat in another window
echo ============================================================
echo.

:LOOP
if exist "%STOP_FILE%" goto STOPPED
if exist "%ROTATE_LOG%" call "%ROTATE_LOG%" "%OUTPUT_DIR%"

set "RUN_STARTED=%date% %time%"
>>"%LOOP_LOG%" echo [!RUN_STARTED!] RUN_ONCE_START
call "%RUN_ONCE%" --loop
set "RUN_EXIT=!ERRORLEVEL!"
set "RUN_ENDED=%date% %time%"

if "!RUN_EXIT!"=="0" (
  echo [!RUN_ENDED!] PASS
  >>"%LOOP_LOG%" echo [!RUN_ENDED!] RUN_ONCE_PASS
) else if "!RUN_EXIT!"=="5" (
  echo [!RUN_ENDED!] DEFERRED - MT5 files or M1 entry row are not ready
  >>"%LOOP_LOG%" echo [!RUN_ENDED!] RUN_ONCE_DEFERRED
) else if "!RUN_EXIT!"=="4" (
  echo [!RUN_ENDED!] BUSY - another one-shot process is running
  >>"%LOOP_LOG%" echo [!RUN_ENDED!] RUN_ONCE_BUSY
) else (
  echo [!RUN_ENDED!] FAIL exit_code=!RUN_EXIT! - loop continues
  >>"%LOOP_LOG%" echo [!RUN_ENDED!] RUN_ONCE_FAIL exit_code=!RUN_EXIT!
)

if exist "%STOP_FILE%" goto STOPPED

timeout /t %GML1_LIVE_INTERVAL_SECONDS% /nobreak >nul
goto LOOP

:STOPPED
set "STOPPED_AT=%date% %time%"
>>"%LOOP_LOG%" echo [!STOPPED_AT!] LOOP_STOP
del /q "%STOP_FILE%" >nul 2>&1
rmdir "%LOCK_DIR%" >nul 2>&1
echo.
echo Live loop stopped normally.
echo Log: "%LOOP_LOG%"
echo.
pause
exit /b 0
