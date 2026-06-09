@echo off
setlocal EnableExtensions

rem GOLD V3 15 audit-only replay execution runner.
rem Runtime BAT location: scripts\gold_v3_runtime\bat\
rem This BAT executes only the Stage 15 audit-only replay from existing GOLD V3 Stage 14 and Stage 05 artifacts.
rem It must not approve final candidates, finalize thresholds, train models, generate signals, create ZIP output,
rem call AI APIs, notify Discord, place MT5 orders, or enable live hooks/evaluators/final signals.
rem
rem 2026-06-09 fix: run through gold_v3_15_audit_only_replay_execution_fixed_runner.py
rem to patch the sha256_file sentinel bug in the original Stage 15 module.

set "EXIT_CODE=1"

echo ============================================================
echo GOLD V3 15 AUDIT-ONLY REPLAY EXECUTION
echo Runtime BAT: scripts\gold_v3_runtime\bat\GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION.bat
echo ============================================================
echo.

cd /d "%~dp0\..\..\.."
if errorlevel 1 goto FATAL_CD

set "REPO_ROOT=%CD%"
set "SCRIPT_PATH=scripts\gold_v3_runtime\gold_v3_15_audit_only_replay_execution_fixed_runner.py"

echo [GOLD_V3_15] repo_root=%REPO_ROOT%
echo [GOLD_V3_15] script=%SCRIPT_PATH%
echo [GOLD_V3_15] expected input: Stage 14 READY replay-plan preview and Stage 05 READY label-feature join rows
echo [GOLD_V3_15] allowed: audit-only replay execution only
echo [GOLD_V3_15] forbidden: final approval/threshold/training/signal/ZIP/AI/Discord/MT5/live/final signal
echo.

if not exist "%SCRIPT_PATH%" goto FATAL_SCRIPT

where py >nul 2>nul
if not errorlevel 1 goto RUN_PY

where python >nul 2>nul
if not errorlevel 1 goto RUN_PYTHON

echo [GOLD_V3_15] BLOCKED: Python launcher not found.
set "EXIT_CODE=1"
goto END_HOLD

:RUN_PY
echo [GOLD_V3_15] using py -3
py -3 "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:RUN_PYTHON
echo [GOLD_V3_15] using python
python "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:AFTER_RUN
echo.
if "%EXIT_CODE%"=="0" (
  echo [GOLD_V3_15] READY audit-only replay outputs written.
  echo [GOLD_V3_15] This is NOT final approval and NOT live approval.
) else (
  echo [GOLD_V3_15] BLOCKED or FAILED. script_exit_code=%EXIT_CODE%
)
goto END_HOLD

:FATAL_CD
echo [GOLD_V3_15] FATAL: could not move to repository root.
echo [GOLD_V3_15] bat_dir=%~dp0
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_SCRIPT
echo [GOLD_V3_15] FATAL: runtime script not found.
echo [GOLD_V3_15] missing=%SCRIPT_PATH%
set "EXIT_CODE=1"
goto END_HOLD

:END_HOLD
echo.
echo ============================================================
echo [GOLD_V3_15] exit_code=%EXIT_CODE%
echo [GOLD_V3_15] Press any key to close this window.
echo ============================================================
pause
exit /b %EXIT_CODE%
