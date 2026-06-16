@echo off
setlocal EnableExtensions

cd /d "%~dp0\..\..\.."

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 195 --message "BAT_START stage195 audit"
if errorlevel 1 echo [WARN] progress marker failed at BAT_START. Continue.

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 195 --message "RUN_STAGE195_SCRIPT"
py -3 scripts\gold_v3_runtime\gold_v3_195_scalp_one_position_decomposition_audit.py %*
set EXITCODE=%ERRORLEVEL%

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 195 --message "BAT_END exitcode=%EXITCODE%"
if not "%EXITCODE%"=="0" pause

endlocal & exit /b %EXITCODE%
