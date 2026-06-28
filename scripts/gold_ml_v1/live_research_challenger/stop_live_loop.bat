@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "STOP_FILE=%SCRIPT_DIR%STOP_LIVE_LOOP"

>"%STOP_FILE%" echo stop_requested=%date% %time%
echo Stop request created.
echo The live loop will stop after the current run or timeout finishes.
echo File: "%STOP_FILE%"
echo.
pause
exit /b 0
