@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "LOCK_DIR=%SCRIPT_DIR%live_loop.lock"
set "STOP_FILE=%SCRIPT_DIR%STOP_LIVE_LOOP"

if exist "%LOCK_DIR%" (
  rmdir /s /q "%LOCK_DIR%"
  echo Removed stale lock: "%LOCK_DIR%"
) else (
  echo No lock directory exists.
)

if exist "%STOP_FILE%" (
  del /q "%STOP_FILE%"
  echo Removed stale stop file: "%STOP_FILE%"
)

echo.
echo Use this only when no live loop window is running.
echo.
pause
exit /b 0
