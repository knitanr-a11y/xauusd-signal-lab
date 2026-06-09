@echo off
setlocal EnableExtensions

rem GOLD V3 16 all replay result review and narrowing audit-only runner.
rem Runtime BAT location: scripts\gold_v3_runtime\bat\
rem This BAT reviews all Stage 15 replay candidates, including rank 4/6/7/8 h1_atr56 comparison profiles.
rem It must not approve final candidates, finalize thresholds, train models, generate signals, create ZIP output,
rem call AI APIs, notify Discord, place MT5 orders, or enable live hooks/evaluators/final signals.
rem
rem 2026-06-09 fix: run through gold_v3_16_all_replay_result_review_and_narrowing_fixed_runner.py
rem to avoid duplicate safety-key expansion in the original Stage 16 module summary.

set "EXIT_CODE=1"

echo ============================================================
echo GOLD V3 16 ALL REPLAY RESULT REVIEW AND NARROWING - AUDIT ONLY
echo Runtime BAT: scripts\gold_v3_runtime\bat\GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_AUDIT_ONLY.bat
echo ============================================================
echo.

cd /d "%~dp0\..\..\.."
if errorlevel 1 goto FATAL_CD

set "REPO_ROOT=%CD%"
set "SCRIPT_PATH=scripts\gold_v3_runtime\gold_v3_16_all_replay_result_review_and_narrowing_fixed_runner.py"

echo [GOLD_V3_16] repo_root=%REPO_ROOT%
echo [GOLD_V3_16] script=%SCRIPT_PATH%
echo [GOLD_V3_16] expected input: Stage 15 READY replay outputs
echo [GOLD_V3_16] scope: all 7 candidates, including deferred/narrow h1_atr56 profiles
echo [GOLD_V3_16] forbidden: final approval/threshold/training/signal/ZIP/AI/Discord/MT5/live/final signal
echo.

if not exist "%SCRIPT_PATH%" goto FATAL_SCRIPT

where py >nul 2>nul
if not errorlevel 1 goto RUN_PY

where python >nul 2>nul
if not errorlevel 1 goto RUN_PYTHON

echo [GOLD_V3_16] BLOCKED: Python launcher not found.
set "EXIT_CODE=1"
goto END_HOLD

:RUN_PY
echo [GOLD_V3_16] using py -3
py -3 "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:RUN_PYTHON
echo [GOLD_V3_16] using python
python "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:AFTER_RUN
echo.
if "%EXIT_CODE%"=="0" (
  echo [GOLD_V3_16] READY all-candidate review outputs written.
  echo [GOLD_V3_16] This is NOT final approval and NOT live approval.
) else (
  echo [GOLD_V3_16] BLOCKED or FAILED. script_exit_code=%EXIT_CODE%
)
goto END_HOLD

:FATAL_CD
echo [GOLD_V3_16] FATAL: could not move to repository root.
echo [GOLD_V3_16] bat_dir=%~dp0
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_SCRIPT
echo [GOLD_V3_16] FATAL: runtime script not found.
echo [GOLD_V3_16] missing=%SCRIPT_PATH%
set "EXIT_CODE=1"
goto END_HOLD

:END_HOLD
echo.
echo ============================================================
echo [GOLD_V3_16] exit_code=%EXIT_CODE%
echo [GOLD_V3_16] Press any key to close this window.
echo ============================================================
pause
exit /b %EXIT_CODE%
