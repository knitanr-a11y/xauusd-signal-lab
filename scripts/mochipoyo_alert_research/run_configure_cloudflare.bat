@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%configure_cloudflare.py"

if not exist "%PYTHON_SCRIPT%" (
  echo [ERROR] Configuration helper was not found:
  echo "%PYTHON_SCRIPT%"
  pause
  exit /b 2
)

py -3.12 "%PYTHON_SCRIPT%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo Local configuration step completed.
) else (
  echo Configuration step failed or was cancelled. Exit code: %EXITCODE%
)
echo.
pause
exit /b %EXITCODE%
