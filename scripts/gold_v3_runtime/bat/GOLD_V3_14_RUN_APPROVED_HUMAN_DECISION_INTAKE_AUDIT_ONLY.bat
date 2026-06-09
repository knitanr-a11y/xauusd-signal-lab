@echo off
setlocal EnableExtensions

rem GOLD V3 14 user-approved human decision intake audit-only runner.
rem Runtime BAT location: scripts\gold_v3_runtime\bat\
rem This BAT reruns Stage 14 using the user-confirmed human decision CSV.
rem It only creates/updates Stage 14 intake outputs and replay-plan preview.
rem It must not execute replay, approve final candidates, finalize thresholds,
rem train models, generate signals, create ZIP output, call AI APIs, notify Discord,
rem place MT5 orders, or enable live hooks/evaluators/final signals.

set "EXIT_CODE=1"

echo ============================================================
echo GOLD V3 14 APPROVED HUMAN DECISION INTAKE - AUDIT ONLY
echo Runtime BAT: scripts\gold_v3_runtime\bat\GOLD_V3_14_RUN_APPROVED_HUMAN_DECISION_INTAKE_AUDIT_ONLY.bat
echo ============================================================
echo.

cd /d "%~dp0\..\..\.."
if errorlevel 1 goto FATAL_CD

set "REPO_ROOT=%CD%"
set "SCRIPT_PATH=scripts\gold_v3_runtime\gold_v3_14_human_ranking_decision_intake_audit_only.py"
set "DECISION_INPUT=scripts\gold_v3_runtime\human_decisions\gold_v3_14_human_decision_intake_APPROVED_USER_CONFIRMED_20260609.csv"

echo [GOLD_V3_14_APPROVED] repo_root=%REPO_ROOT%
echo [GOLD_V3_14_APPROVED] script=%SCRIPT_PATH%
echo [GOLD_V3_14_APPROVED] human_decision_input=%DECISION_INPUT%
echo [GOLD_V3_14_APPROVED] expected: 7 APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY, 1 REQUEST_MORE_AUDIT
echo [GOLD_V3_14_APPROVED] forbidden: replay/final approval/threshold/training/signal/ZIP/AI/Discord/MT5/live/final signal
echo.

if not exist "%SCRIPT_PATH%" goto FATAL_SCRIPT
if not exist "%DECISION_INPUT%" goto FATAL_DECISION_INPUT

where py >nul 2>nul
if not errorlevel 1 goto RUN_PY

where python >nul 2>nul
if not errorlevel 1 goto RUN_PYTHON

echo [GOLD_V3_14_APPROVED] BLOCKED: Python launcher not found.
set "EXIT_CODE=1"
goto END_HOLD

:RUN_PY
echo [GOLD_V3_14_APPROVED] using py -3
py -3 "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%" --human-decision-input "%DECISION_INPUT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:RUN_PYTHON
echo [GOLD_V3_14_APPROVED] using python
python "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%" --human-decision-input "%DECISION_INPUT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:AFTER_RUN
echo.
if "%EXIT_CODE%"=="0" (
  echo [GOLD_V3_14_APPROVED] READY audit-only intake/replay-plan preview.
  echo [GOLD_V3_14_APPROVED] Replay execution was NOT run.
) else (
  echo [GOLD_V3_14_APPROVED] BLOCKED, INPUT REVIEW REQUIRED, or FAILED. script_exit_code=%EXIT_CODE%
)
goto END_HOLD

:FATAL_CD
echo [GOLD_V3_14_APPROVED] FATAL: could not move to repository root.
echo [GOLD_V3_14_APPROVED] bat_dir=%~dp0
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_SCRIPT
echo [GOLD_V3_14_APPROVED] FATAL: runtime script not found.
echo [GOLD_V3_14_APPROVED] missing=%SCRIPT_PATH%
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_DECISION_INPUT
echo [GOLD_V3_14_APPROVED] FATAL: human decision input CSV not found.
echo [GOLD_V3_14_APPROVED] missing=%DECISION_INPUT%
set "EXIT_CODE=1"
goto END_HOLD

:END_HOLD
echo.
echo ============================================================
echo [GOLD_V3_14_APPROVED] exit_code=%EXIT_CODE%
echo [GOLD_V3_14_APPROVED] Press any key to close this window.
echo ============================================================
pause
exit /b %EXIT_CODE%
