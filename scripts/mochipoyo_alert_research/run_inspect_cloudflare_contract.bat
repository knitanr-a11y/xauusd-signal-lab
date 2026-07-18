@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%inspect_cloudflare_contract.py"

if not exist "%PYTHON_SCRIPT%" (
  echo [ERROR] Contract inspector was not found:
  echo "%PYTHON_SCRIPT%"
  pause
  exit /b 2
)

echo ============================================================
echo Mochipoyo Cloudflare contract inspection - READ ONLY
echo Values         : NOT DISPLAYED
echo Secrets        : NOT DISPLAYED
echo Database write : OFF
echo Cursor update  : OFF
echo Discord send   : OFF
echo MT5 orders     : OFF
echo ============================================================
echo.

py -3.12 "%PYTHON_SCRIPT%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [PASS] Contract shape inspection completed.
  echo Copy the JSON above. It contains key names and data types only.
) else (
  echo [FAIL] Contract shape inspection failed. Exit code: %EXITCODE%
)
echo.
pause
exit /b %EXITCODE%
