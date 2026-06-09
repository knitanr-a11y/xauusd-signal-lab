@echo off
setlocal EnableExtensions

rem GOLD V3 18 monthly stability final audit shortlist audit-only runner.
rem Runtime BAT location: scripts\gold_v3_runtime\bat\
rem This BAT audits monthly stability for Stage 17 shortlist scenarios.
rem It must not approve final candidates, finalize thresholds, train models, generate signals, create ZIP output,
rem call AI APIs, notify Discord, place MT5 orders, or enable live hooks/evaluators/final signals.

set "EXIT_CODE=1"

echo ============================================================
echo GOLD V3 18 MONTHLY STABILITY FINAL AUDIT SHORTLIST - AUDIT ONLY
echo Runtime BAT: scripts\gold_v3_runtime\bat\GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_AUDIT_ONLY.bat
echo ============================================================
echo.

cd /d "%~dp0\..\..\.."
if errorlevel 1 goto FATAL_CD

set "REPO_ROOT=%CD%"
set "SCRIPT_PATH=scripts\gold_v3_runtime\gold_v3_18_monthly_stability_final_audit_shortlist_audit_only.py"

echo [GOLD_V3_18] repo_root=%REPO_ROOT%
echo [GOLD_V3_18] script=%SCRIPT_PATH%
echo [GOLD_V3_18] expected input: Stage 15 READY ledger, Stage 16 READY review, Stage 17 READY spacing outputs
echo [GOLD_V3_18] scope: monthly stability for primary/auxiliary/diagnostic shortlist, rank 7/8 visible as weak diagnostic profiles
echo [GOLD_V3_18] forbidden: final approval/threshold/training/signal/ZIP/AI/Discord/MT5/live/final signal
echo.

if not exist "%SCRIPT_PATH%" goto FATAL_SCRIPT

where py >nul 2>nul
if not errorlevel 1 goto RUN_PY

where python >nul 2>nul
if not errorlevel 1 goto RUN_PYTHON

echo [GOLD_V3_18] BLOCKED: Python launcher not found.
set "EXIT_CODE=1"
goto END_HOLD

:RUN_PY
echo [GOLD_V3_18] using py -3
py -3 "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:RUN_PYTHON
echo [GOLD_V3_18] using python
python "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:AFTER_RUN
echo.
if "%EXIT_CODE%"=="0" (
  echo [GOLD_V3_18] READY monthly stability final audit shortlist outputs written.
  echo [GOLD_V3_18] This is NOT final approval and NOT live approval.
) else (
  echo [GOLD_V3_18] BLOCKED or FAILED. script_exit_code=%EXIT_CODE%
)
goto END_HOLD

:FATAL_CD
echo [GOLD_V3_18] FATAL: could not move to repository root.
echo [GOLD_V3_18] bat_dir=%~dp0
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_SCRIPT
echo [GOLD_V3_18] FATAL: runtime script not found.
echo [GOLD_V3_18] missing=%SCRIPT_PATH%
set "EXIT_CODE=1"
goto END_HOLD

:END_HOLD
echo.
echo ============================================================
echo [GOLD_V3_18] exit_code=%EXIT_CODE%
echo [GOLD_V3_18] Press any key to close this window.
echo ============================================================
pause
exit /b %EXIT_CODE%
