@echo off
setlocal EnableExtensions

cd /d "%~dp0\..\..\.."

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 178 --message "BAT_START audit-only cost spread slippage monthly robustness"
if errorlevel 1 (
  echo [WARN] progress marker failed at BAT_START. Continue audit script.
)

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 178 --message "RUN_STAGE178_SCRIPT"
py -3 scripts\gold_v3_runtime\gold_v3_178_cost_spread_slippage_monthly_robustness_audit.py %*
set EXITCODE=%ERRORLEVEL%

py -3 scripts\gold_v3_runtime\gold_v3_progress_marker.py --stage 178 --message "BAT_END exitcode=%EXITCODE%"
if not "%EXITCODE%"=="0" pause

endlocal & exit /b %EXITCODE%
