@echo off
setlocal EnableExtensions
set "OUTPUT_DIR=%~1"
if "%OUTPUT_DIR%"=="" exit /b 0
set "CURRENT_LOG=%OUTPUT_DIR%\live_loop.log"
set "PREVIOUS_LOG=%OUTPUT_DIR%\live_loop.previous.log"
if not defined GML1_LIVE_LOOP_MAX_LOG_BYTES set "GML1_LIVE_LOOP_MAX_LOG_BYTES=5242880"
if not exist "%CURRENT_LOG%" exit /b 0
for %%A in ("%CURRENT_LOG%") do set "CURRENT_SIZE=%%~zA"
if %CURRENT_SIZE% LSS %GML1_LIVE_LOOP_MAX_LOG_BYTES% exit /b 0
if exist "%PREVIOUS_LOG%" del /q "%PREVIOUS_LOG%" >nul 2>&1
move /y "%CURRENT_LOG%" "%PREVIOUS_LOG%" >nul 2>&1
exit /b 0
