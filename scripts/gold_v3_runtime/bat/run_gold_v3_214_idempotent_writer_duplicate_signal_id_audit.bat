@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_214_idempotent_writer_duplicate_signal_id_audit.py %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" pause
endlocal & exit /b %EXITCODE%
