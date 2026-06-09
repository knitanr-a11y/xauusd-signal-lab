@echo off
setlocal EnableExtensions

rem GOLD V3 13 ranking decision template audit-only runner.
rem This BAT only creates the stage-13 audit template from existing stage-12 outputs.
rem It must not run replay, train models, generate signals, create ZIPs, call AI APIs,
rem notify Discord, place MT5 orders, or enable live hooks/evaluators.
rem The console is intentionally held open with PAUSE so errors remain visible.

set "REPO_ROOT=%~dp0"
pushd "%REPO_ROOT%" >nul
if errorlevel 1 (
    echo [GOLD_V3_13] FATAL: failed to enter repo root: %REPO_ROOT%
    set "RUN_EXIT=1"
    goto :END_HOLD
)

set "OUTPUT_DIR=%CD%\Files\FX_OUTPUTS\gold_v3\13_ranking_decision_template_audit_only"
if not exist "%OUTPUT_DIR%\" mkdir "%OUTPUT_DIR%" 2>nul
if not exist "%OUTPUT_DIR%\" (
    echo [GOLD_V3_13] FATAL: failed to create output_dir=%OUTPUT_DIR%
    set "RUN_EXIT=1"
    goto :END_HOLD
)

echo [GOLD_V3_13] AUDIT-ONLY ranking decision template
echo [GOLD_V3_13] repo_root=%CD%
echo [GOLD_V3_13] output_dir=%OUTPUT_DIR%
echo [GOLD_V3_13] forbidden: replay/training/signal/ZIP/AI/Discord/MT5/live/final approval
echo.

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

:END_HOLD
echo.
echo [GOLD_V3_13] exit_code=%RUN_EXIT%
echo [GOLD_V3_13] Press any key to close this window.
pause >nul
popd >nul 2>nul
exit /b %RUN_EXIT%
