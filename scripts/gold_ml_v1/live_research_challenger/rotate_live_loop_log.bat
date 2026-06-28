@echo off
setlocal EnableExtensions
set "OUTPUT_DIR=%~1"
if "%OUTPUT_DIR%"=="" exit /b 0
set "SCRIPT_DIR=%~dp0"
set "ROTATOR=%SCRIPT_DIR%rotate_live_loop_log.py"
if not defined GML1_LIVE_LOOP_MAX_LOG_BYTES set "GML1_LIVE_LOOP_MAX_LOG_BYTES=5242880"
if not exist "%ROTATOR%" exit /b 0
py -3.12 "%ROTATOR%" "%OUTPUT_DIR%" --max-bytes %GML1_LIVE_LOOP_MAX_LOG_BYTES% >nul 2>&1
exit /b %ERRORLEVEL%
