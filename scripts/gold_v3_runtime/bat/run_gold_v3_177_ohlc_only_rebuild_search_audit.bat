@echo off
setlocal EnableExtensions

cd /d "%~dp0\..\..\.."

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 177 --message "BAT_START audit-only OHLC-only rebuild search"
if errorlevel 1 (
  echo [WARN] progress marker failed at BAT_START. Continue audit script.
)

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 177 --message "RUN_STAGE177_SCRIPT"
py -3 scripts\gold_v3_runtime\gold_v3_177_ohlc_only_rebuild_search_audit_entry.py %*
set EXITCODE=%ERRORLEVEL%

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 177 --message "BAT_END exitcode=%EXITCODE%"
if not "%EXITCODE%"=="0" pause

endlocal & exit /b %EXITCODE%
