@echo off
setlocal EnableExtensions

cd /d "%~dp0\..\..\.."

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 179 --message "BAT_START audit-only monthly winrate tradecount"
if errorlevel 1 (
  echo [WARN] progress marker failed at BAT_START. Continue audit script.
)

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 179 --message "RUN_STAGE179_SCRIPT"
py -3 scripts\gold_v3_runtime\gold_v3_179_monthly_winrate_tradecount_audit.py %*
set EXITCODE=%ERRORLEVEL%

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 179 --message "BAT_END exitcode=%EXITCODE%"
if not "%EXITCODE%"=="0" pause

endlocal & exit /b %EXITCODE%
