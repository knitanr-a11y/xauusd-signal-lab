@echo off
setlocal EnableExtensions

rem GOLD V3 19 final audit shortlist human decision template audit-only runner.
rem Runtime BAT location: scripts\gold_v3_runtime\bat\
rem This BAT creates a human decision template from Stage 18 monthly stability results.
rem It must not approve final candidates, finalize thresholds, train models, generate signals, create ZIP output,
rem call AI APIs, notify Discord, place MT5 orders, or enable live hooks/evaluators/final signals.

set "EXIT_CODE=1"

echo ============================================================
echo GOLD V3 19 FINAL AUDIT SHORTLIST HUMAN DECISION TEMPLATE - AUDIT ONLY
echo Runtime BAT: scripts\gold_v3_runtime\bat\GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_AUDIT_ONLY.bat
echo ============================================================
echo.

cd /d "%~dp0\..\..\.."
if errorlevel 1 goto FATAL_CD

set "REPO_ROOT=%CD%"
set "SCRIPT_PATH=scripts\gold_v3_runtime\gold_v3_19_final_audit_shortlist_human_decision_template_audit_only.py"

echo [GOLD_V3_19] repo_root=%REPO_ROOT%
echo [GOLD_V3_19] script=%SCRIPT_PATH%
echo [GOLD_V3_19] expected input: Stage 18 READY monthly stability shortlist outputs
echo [GOLD_V3_19] scope: create human decision template only; no automatic decision execution
echo [GOLD_V3_19] forbidden: final approval/threshold/training/signal/ZIP/AI/Discord/MT5/live/final signal
echo.

if not exist "%SCRIPT_PATH%" goto FATAL_SCRIPT

where py >nul 2>nul
if not errorlevel 1 goto RUN_PY

where python >nul 2>nul
if not errorlevel 1 goto RUN_PYTHON

echo [GOLD_V3_19] BLOCKED: Python launcher not found.
set "EXIT_CODE=1"
goto END_HOLD

:RUN_PY
echo [GOLD_V3_19] using py -3
py -3 "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:RUN_PYTHON
echo [GOLD_V3_19] using python
python "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:AFTER_RUN
echo.
if "%EXIT_CODE%"=="0" (
  echo [GOLD_V3_19] READY human decision template outputs written.
  echo [GOLD_V3_19] This is NOT final approval and NOT live approval.
) else (
  echo [GOLD_V3_19] BLOCKED or FAILED. script_exit_code=%EXIT_CODE%
)
goto END_HOLD

:FATAL_CD
echo [GOLD_V3_19] FATAL: could not move to repository root.
echo [GOLD_V3_19] bat_dir=%~dp0
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_SCRIPT
echo [GOLD_V3_19] FATAL: runtime script not found.
echo [GOLD_V3_19] missing=%SCRIPT_PATH%
set "EXIT_CODE=1"
goto END_HOLD

:END_HOLD
echo.
echo ============================================================
echo [GOLD_V3_19] exit_code=%EXIT_CODE%
echo [GOLD_V3_19] Press any key to close this window.
echo ============================================================
pause
exit /b %EXIT_CODE%
