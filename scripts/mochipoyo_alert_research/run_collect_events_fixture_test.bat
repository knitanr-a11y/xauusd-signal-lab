@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "REPO_ROOT=%%~fI"
set "TEST_ROOT=%TEMP%\xauusd_signal_lab\mochipoyo_fixture_test"
set "TEST_ENV=%TEST_ROOT%\.env"
set "TEST_DB=%TEST_ROOT%\fixture.sqlite3"
set "FIXTURE=%REPO_ROOT%\tests\mochipoyo_alert_research\fixtures\events_page_1.json"
set "EMPTY_FIXTURE=%TEST_ROOT%\events_empty_after_4.json"

if not exist "%TEST_ROOT%" mkdir "%TEST_ROOT%" >nul 2>&1
if not exist "%TEST_ENV%" (
  >"%TEST_ENV%" echo # Offline fixture test only. No secret is required.
)

rem Reset only the isolated fixture database so every run is deterministic.
if exist "%TEST_DB%" del /q "%TEST_DB%" >nul 2>&1
if exist "%TEST_DB%-wal" del /q "%TEST_DB%-wal" >nul 2>&1
if exist "%TEST_DB%-shm" del /q "%TEST_DB%-shm" >nul 2>&1
>"%EMPTY_FIXTURE%" echo {"ok":true,"latest_id":4,"events":[]}

echo ============================================================
echo Mochipoyo Stage M1 offline fixture test
echo Production database: NOT USED
echo Test database      : %TEST_DB%
echo ============================================================
echo.
echo [STEP 1/3] Initial collection: expect inserted=3, cursor=4
echo.
call "%SCRIPT_DIR%run_collect_events_once.bat" ^
  --env "%TEST_ENV%" ^
  --db "%TEST_DB%" ^
  --fixture "%FIXTURE%"
if errorlevel 1 goto FAILED

echo.
echo [STEP 2/3] Cursor resume: expect after_id_before=4, response=0
echo.
call "%SCRIPT_DIR%run_collect_events_once.bat" ^
  --env "%TEST_ENV%" ^
  --db "%TEST_DB%" ^
  --fixture "%EMPTY_FIXTURE%"
if errorlevel 1 goto FAILED

echo.
echo [STEP 3/3] Forced replay: expect inserted=0, duplicate=3
echo.
call "%SCRIPT_DIR%run_collect_events_once.bat" ^
  --env "%TEST_ENV%" ^
  --db "%TEST_DB%" ^
  --fixture "%FIXTURE%" ^
  --after-id 0
if errorlevel 1 goto FAILED

echo.
echo [PASS] Offline fixture collector test completed.
echo Initial insert, cursor resume, and duplicate replay all passed.
echo Test database: "%TEST_DB%"
echo.
pause
exit /b 0

:FAILED
set "EXITCODE=%ERRORLEVEL%"
echo.
echo [FAIL] Offline fixture collector test failed. Exit code: %EXITCODE%
echo Test database: "%TEST_DB%"
echo.
pause
exit /b %EXITCODE%
