@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "REPO_ROOT=%%~fI"
set "PYTHON_SCRIPT=%SCRIPT_DIR%collect_events_once.py"

if not exist "%PYTHON_SCRIPT%" (
  echo [ERROR] Mochipoyo collector was not found:
  echo "%PYTHON_SCRIPT%"
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo alert collector - Stage M1 audit-only
echo Discord send : OFF
echo MT5 orders   : OFF
echo Live ready   : OFF
echo Final signal : OFF
echo ============================================================

pushd "%REPO_ROOT%" >nul
py -3.12 "%PYTHON_SCRIPT%" %*
set "EXITCODE=%ERRORLEVEL%"
popd >nul

if not "%EXITCODE%"=="0" (
  echo.
  echo [ERROR] Collector failed with exit code %EXITCODE%.
  echo No cursor is advanced when event validation or storage fails.
  pause
)

exit /b %EXITCODE%
