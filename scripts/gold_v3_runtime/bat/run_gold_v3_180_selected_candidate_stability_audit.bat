@echo off
setlocal EnableExtensions

cd /d "%~dp0\..\..\.."

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 180 --message "BAT_START audit-only selected candidate stability"
if errorlevel 1 (
  echo [WARN] progress marker failed at BAT_START. Continue audit script.
)

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 180 --message "RUN_STAGE180_SCRIPT"
py -3 scripts\gold_v3_runtime\gold_v3_180_selected_candidate_stability_audit.py %*
set EXITCODE=%ERRORLEVEL%

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 180 --message "BAT_END exitcode=%EXITCODE%"
if not "%EXITCODE%"=="0" pause

endlocal & exit /b %EXITCODE%
