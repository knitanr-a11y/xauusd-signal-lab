@echo off
setlocal

REM GOLD V3 Stage107 audit-only runner.
REM Do not use GOLD V2 / old GOLD / DISC8 / Stage41 as trading source.
REM Do not mutate source CSVs, CSV contract, candidate pool, Stage45, Stage69, runtime, live evaluator, or final signal.
REM CSV latest row is contractually closed. open/as-of treatment is forbidden.

set "BAT_DIR=%~dp0"
pushd "%BAT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

REM Optional: user may set MT5_FILES_DIR externally. If unset, repo root is used as MT5 Files-like root.
if "%MT5_FILES_DIR%"=="" set "MT5_FILES_DIR=%REPO_ROOT%"

set "OUT_DIR=%MT5_FILES_DIR%\FX_OUTPUTS\gold_v3\107c"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_107_normal_and_hv_direction_assumption_audit.py" --mt5-files-dir "%MT5_FILES_DIR%" %*
set "EXITCODE=%ERRORLEVEL%"

echo.
echo Stage107 finished with exit code %EXITCODE%.
echo BAT path:
echo   scripts\gold_v3_runtime\bat\run_gold_v3_107_normal_and_hv_direction_assumption.bat
echo Paste this file back into ChatGPT:
echo   %OUT_DIR%\paste_me.txt
echo Expected READY status:
echo   GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_READY_AUDIT_ONLY
echo Blocked status is acceptable if inputs are incomplete:
echo   BLOCKED_INPUT_INCOMPLETE_AUDIT_ARTIFACTS_WRITTEN
echo.

popd
exit /b %EXITCODE%
