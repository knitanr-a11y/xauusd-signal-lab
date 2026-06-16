@echo off
setlocal EnableExtensions

cd /d "%~dp0\..\..\.."

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 203 --message "BAT_START stage203 audit"
if errorlevel 1 echo [WARN] progress marker failed at BAT_START. Continue.

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 203 --message "RUN_STAGE203_SCRIPT"
py -3 scripts\gold_v3_runtime\gold_v3_203_retention_writer_dry_run_audit.py %*
set EXITCODE=%ERRORLEVEL%

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 203 --message "BAT_END exitcode=%EXITCODE%"
if not "%EXITCODE%"=="0" pause

endlocal & exit /b %EXITCODE%
