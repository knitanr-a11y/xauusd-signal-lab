@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_211_integrated_no_send_cycle_runner_audit.py %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" pause
endlocal & exit /b %EXITCODE%
