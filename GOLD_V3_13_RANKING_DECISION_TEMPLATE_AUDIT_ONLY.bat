@echo off
setlocal

rem GOLD V3 13 ranking decision template audit-only runner.
rem This BAT only creates the stage-13 audit template from existing stage-12 outputs.
rem It must not run replay, train models, generate signals, create ZIPs, call AI APIs,
rem notify Discord, place MT5 orders, or enable live hooks/evaluators.

set "REPO_ROOT=%~dp0"
pushd "%REPO_ROOT%" >nul

set "OUTPUT_DIR=Files\FX_OUTPUTS\gold_v3\13_ranking_decision_template_audit_only"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD_V3_13] AUDIT-ONLY ranking decision template
echo [GOLD_V3_13] output_dir=%CD%\%OUTPUT_DIR%
echo [GOLD_V3_13] forbidden: replay/training/signal/ZIP/AI/Discord/MT5/live/final approval

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 scripts\gold_v3_13_ranking_decision_template_audit_only.py --repo-root "%CD%"
    set "RUN_EXIT=%ERRORLEVEL%"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL%==0 (
        python scripts\gold_v3_13_ranking_decision_template_audit_only.py --repo-root "%CD%"
        set "RUN_EXIT=%ERRORLEVEL%"
    ) else (
        echo [GOLD_V3_13] BLOCKED: Python launcher not found. > "%OUTPUT_DIR%\gold_v3_13_bat_blocked_no_python.txt"
        echo [GOLD_V3_13] BLOCKED: Python launcher not found.
        set "RUN_EXIT=1"
    )
)

echo [GOLD_V3_13] exit_code=%RUN_EXIT%
popd >nul
exit /b %RUN_EXIT%
