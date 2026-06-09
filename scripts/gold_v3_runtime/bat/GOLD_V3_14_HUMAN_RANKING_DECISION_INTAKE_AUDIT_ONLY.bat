@echo off
setlocal EnableExtensions

rem GOLD V3 14 human ranking decision intake audit-only runner.
rem Runtime BAT location: scripts\gold_v3_runtime\bat\
rem This BAT only creates or validates human decision intake rows and writes an
rem audit-only replay-plan preview from GOLD V3 Stage 13 outputs.
rem It must not execute replay, approve final candidates, finalize thresholds,
rem train models, generate signals, create ZIP output, call AI APIs, notify Discord,
rem place MT5 orders, or enable live hooks/evaluators/final signals.

set "EXIT_CODE=1"

echo ============================================================
echo GOLD V3 14 HUMAN RANKING DECISION INTAKE - AUDIT ONLY
echo Runtime BAT: scripts\gold_v3_runtime\bat\GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_AUDIT_ONLY.bat
echo ============================================================
echo.

cd /d "%~dp0\..\..\.."
if errorlevel 1 goto FATAL_CD

set "REPO_ROOT=%CD%"
set "SCRIPT_PATH=scripts\gold_v3_runtime\gold_v3_14_human_ranking_decision_intake_audit_only.py"

echo [GOLD_V3_14] repo_root=%REPO_ROOT%
echo [GOLD_V3_14] script=%SCRIPT_PATH%
echo [GOLD_V3_14] forbidden: replay/final approval/threshold/training/signal/ZIP/AI/Discord/MT5/live/final signal
echo.

if not exist "%SCRIPT_PATH%" goto FATAL_SCRIPT

where py >nul 2>nul
if not errorlevel 1 goto RUN_PY

where python >nul 2>nul
if not errorlevel 1 goto RUN_PYTHON

echo [GOLD_V3_14] BLOCKED: Python launcher not found.
set "EXIT_CODE=1"
goto END_HOLD

:RUN_PY
echo [GOLD_V3_14] using py -3
py -3 "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:RUN_PYTHON
echo [GOLD_V3_14] using python
python "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:AFTER_RUN
echo.
if "%EXIT_CODE%"=="0" (
  echo [GOLD_V3_14] READY audit-only intake/replay-plan preview.
) else (
  echo [GOLD_V3_14] BLOCKED, INPUT REVIEW REQUIRED, or FAILED. script_exit_code=%EXIT_CODE%
)
goto END_HOLD

:FATAL_CD
echo [GOLD_V3_14] FATAL: could not move to repository root.
echo [GOLD_V3_14] bat_dir=%~dp0
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_SCRIPT
echo [GOLD_V3_14] FATAL: runtime script not found.
echo [GOLD_V3_14] missing=%SCRIPT_PATH%
set "EXIT_CODE=1"
goto END_HOLD

:END_HOLD
echo.
echo ============================================================
echo [GOLD_V3_14] exit_code=%EXIT_CODE%
echo [GOLD_V3_14] Press any key to close this window.
echo ============================================================
pause
exit /b %EXIT_CODE%
