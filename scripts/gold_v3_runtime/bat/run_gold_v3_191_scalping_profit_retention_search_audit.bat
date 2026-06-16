@echo off
setlocal EnableExtensions

cd /d "%~dp0\..\..\.."

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 191 --message "BAT_START stage191 audit"
if errorlevel 1 echo [WARN] progress marker failed at BAT_START. Continue.

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 191 --message "RUN_STAGE191_SCRIPT"
py -3 scripts\gold_v3_runtime\gold_v3_191_scalping_profit_retention_search_audit.py %*
set EXITCODE=%ERRORLEVEL%

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 191 --message "BAT_END exitcode=%EXITCODE%"
if not "%EXITCODE%"=="0" pause

endlocal & exit /b %EXITCODE%
