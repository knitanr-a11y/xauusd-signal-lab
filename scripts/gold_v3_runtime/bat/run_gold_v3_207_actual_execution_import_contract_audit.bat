@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_207_actual_execution_import_contract_audit.py %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" pause
endlocal & exit /b %EXITCODE%
