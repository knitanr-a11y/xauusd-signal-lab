@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_208_signal_id_embedding_contract_audit.py %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" pause
endlocal & exit /b %EXITCODE%
