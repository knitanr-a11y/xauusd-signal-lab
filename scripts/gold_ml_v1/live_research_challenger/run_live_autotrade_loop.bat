@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
set "RUN_ONCE=%SCRIPT_DIR%run_live_connected_once.bat"
set "PROBE=%SCRIPT_DIR%probe_live_inputs.py"
set "ROTATE_LOG=%SCRIPT_DIR%rotate_live_loop_log.bat"
set "STOP_FILE=%SCRIPT_DIR%STOP_LIVE_LOOP"
set "LOCK_DIR=%SCRIPT_DIR%live_loop.lock"
set "OUTPUT_DIR=%REPO_ROOT%\outputs\gold_ml_v1\live_research_challenger"
set "LOOP_LOG=%OUTPUT_DIR%\live_loop.log"

if not defined GML1_LIVE_INTERVAL_SECONDS set "GML1_LIVE_INTERVAL_SECONDS=2"
if not defined GML1_LIVE_IDLE_HEARTBEAT_TICKS set "GML1_LIVE_IDLE_HEARTBEAT_TICKS=30"

if not exist "%RUN_ONCE%" (
  echo ERROR: connected one-shot BAT was not found.
  echo Expected: "%RUN_ONCE%"
  pause
  exit /b 2
)
if not exist "%PROBE%" (
  echo ERROR: probe_live_inputs.py was not found.
  echo Expected: "%PROBE%"
  pause
  exit /b 2
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%" >nul 2>&1
if errorlevel 1 (
  echo ERROR: could not create output directory.
  echo "%OUTPUT_DIR%"
  pause
  exit /b 2
)

mkdir "%LOCK_DIR%" >nul 2>&1
if errorlevel 1 (
  echo ERROR: another GML1 live loop may already be running.
  echo Stop it with stop_live_loop.bat before starting this loop.
  pause
  exit /b 3
)

if exist "%STOP_FILE%" del /q "%STOP_FILE%" >nul 2>&1
if exist "%ROTATE_LOG%" call "%ROTATE_LOG%" "%OUTPUT_DIR%"
set /a IDLE_TICKS=0

>>"%LOOP_LOG%" echo [%date% %time%] AUTOTRADE_LOOP_START interval_seconds=%GML1_LIVE_INTERVAL_SECONDS%
echo ============================================================
echo GML1 Discord and MT5 autotrade loop

echo Full MT5 deal archive is required before trade compaction.
echo ============================================================
echo Poll   : %GML1_LIVE_INTERVAL_SECONDS% seconds
echo Output : %OUTPUT_DIR%
echo Stop   : run stop_live_loop.bat in another window
echo ============================================================
echo.

:LOOP
if exist "%STOP_FILE%" goto STOPPED
if exist "%ROTATE_LOG%" call "%ROTATE_LOG%" "%OUTPUT_DIR%"

py -3.12 "%PROBE%" --output-dir "%OUTPUT_DIR%" --align-seconds %GML1_LIVE_INTERVAL_SECONDS% >nul 2>>"%LOOP_LOG%"
set "PROBE_EXIT=!ERRORLEVEL!"

if "!PROBE_EXIT!"=="10" (
  set /a IDLE_TICKS+=1
  if !IDLE_TICKS! GEQ %GML1_LIVE_IDLE_HEARTBEAT_TICKS% (
    echo [%date% %time%] IDLE - no CSV changes
    >>"%LOOP_LOG%" echo [%date% %time%] IDLE_NO_FILE_CHANGE
    set /a IDLE_TICKS=0
  )
  goto LOOP
)

if not "!PROBE_EXIT!"=="0" (
  echo [%date% %time%] PROBE_FAIL exit_code=!PROBE_EXIT! - loop continues
  >>"%LOOP_LOG%" echo [%date% %time%] PROBE_FAIL exit_code=!PROBE_EXIT!
  goto LOOP
)

set /a IDLE_TICKS=0
call "%RUN_ONCE%" --loop
set "RUN_EXIT=!ERRORLEVEL!"

if "!RUN_EXIT!"=="0" (
  echo [%date% %time%] PASS
  >>"%LOOP_LOG%" echo [%date% %time%] AUTOTRADE_RUN_PASS
) else if "!RUN_EXIT!"=="5" (
  echo [%date% %time%] DEFERRED - waiting for synchronized CSVs
  >>"%LOOP_LOG%" echo [%date% %time%] AUTOTRADE_RUN_DEFERRED
) else if "!RUN_EXIT!"=="4" (
  echo [%date% %time%] BUSY - another one-shot process is running
  >>"%LOOP_LOG%" echo [%date% %time%] AUTOTRADE_RUN_BUSY
) else (
  echo [%date% %time%] FAIL exit_code=!RUN_EXIT! - loop continues
  >>"%LOOP_LOG%" echo [%date% %time%] AUTOTRADE_RUN_FAIL exit_code=!RUN_EXIT!
)

goto LOOP

:STOPPED
>>"%LOOP_LOG%" echo [%date% %time%] AUTOTRADE_LOOP_STOP
del /q "%STOP_FILE%" >nul 2>&1
rmdir "%LOCK_DIR%" >nul 2>&1
echo.
echo Autotrade loop stopped normally.
echo Log: "%LOOP_LOG%"
pause
exit /b 0
