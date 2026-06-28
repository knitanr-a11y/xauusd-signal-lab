@echo off
setlocal
set "LOG=%~dp0run_local_runtime_last.log"

>"%LOG%" echo [%date% %time%] Starting research challenger local runtime
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_local_runtime.ps1" %* >>"%LOG%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

echo.
type "%LOG%"
echo.

if not "%EXIT_CODE%"=="0" (
  echo FAILED. Exit code: %EXIT_CODE%
  echo Log: "%LOG%"
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo PASS.
echo Log: "%LOG%"
echo.
pause
exit /b 0
