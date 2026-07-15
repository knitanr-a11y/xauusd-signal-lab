@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "REPO_ROOT=%%~fI"
set "TEST_ROOT=%TEMP%\xauusd_signal_lab\mochipoyo_fixture_test"
set "TEST_ENV=%TEST_ROOT%\.env"
set "TEST_DB=%TEST_ROOT%\fixture.sqlite3"
set "FIXTURE=%REPO_ROOT%\tests\mochipoyo_alert_research\fixtures\events_page_1.json"

if not exist "%TEST_ROOT%" mkdir "%TEST_ROOT%" >nul 2>&1
if not exist "%TEST_ENV%" (
  >"%TEST_ENV%" echo # Offline fixture test only. No secret is required.
)

echo ============================================================
echo Mochipoyo Stage M1 offline fixture test
echo Production database: NOT USED
echo Test database      : %TEST_DB%
echo ============================================================

call "%SCRIPT_DIR%run_collect_events_once.bat" ^
  --env "%TEST_ENV%" ^
  --db "%TEST_DB%" ^
  --fixture "%FIXTURE%" ^
  --after-id 0

set "EXITCODE=%ERRORLEVEL%"
echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Offline fixture collector test completed.
  echo Test database: "%TEST_DB%"
) else (
  echo [FAIL] Offline fixture collector test failed. Exit code: %EXITCODE%
)
echo.
pause
exit /b %EXITCODE%
