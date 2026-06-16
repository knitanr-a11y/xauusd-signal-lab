@echo off
setlocal EnableExtensions

cd /d "%~dp0\..\..\.."

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 193 --message "BAT_START stage193 audit"
if errorlevel 1 echo [WARN] progress marker failed at BAT_START. Continue.

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 193 --message "RUN_STAGE193_SCRIPT"
py -3 scripts\gold_v3_runtime\gold_v3_193_scalping_profit_stack_portfolio_audit.py %*
set EXITCODE=%ERRORLEVEL%

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 193 --message "BAT_END exitcode=%EXITCODE%"
if not "%EXITCODE%"=="0" pause

endlocal & exit /b %EXITCODE%
