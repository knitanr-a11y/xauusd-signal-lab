@echo off
setlocal EnableExtensions

rem GOLD V3 21 selected pruning rule validation audit-only runner.
rem Includes R1_ONLY_CD60_PRUNE_015 as July rescue candidate.
rem Audit-only. No daily cap. No production or external actions.

set "EXIT_CODE=1"

echo ============================================================
echo GOLD V3 21 SELECTED PRUNING RULE VALIDATION - AUDIT ONLY
echo ============================================================
echo.

cd /d "%~dp0\..\..\.."
if errorlevel 1 goto FATAL_CD

set "REPO_ROOT=%CD%"
set "SCRIPT_PATH=scripts\gold_v3_runtime\gold_v3_21_selected_pruning_rule_validation_audit_only.py"

echo [GOLD_V3_21] repo_root=%REPO_ROOT%
echo [GOLD_V3_21] script=%SCRIPT_PATH%
echo [GOLD_V3_21] scope: selected pruning validation including R1_ONLY_CD60_PRUNE_015.
echo.

if not exist "%SCRIPT_PATH%" goto FATAL_SCRIPT

where py >nul 2>nul
if not errorlevel 1 goto RUN_PY

where python >nul 2>nul
if not errorlevel 1 goto RUN_PYTHON

echo [GOLD_V3_21] BLOCKED: Python launcher not found.
set "EXIT_CODE=1"
goto END_HOLD

:RUN_PY
echo [GOLD_V3_21] using py -3
py -3 "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:RUN_PYTHON
echo [GOLD_V3_21] using python
python "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:AFTER_RUN
echo.
if "%EXIT_CODE%"=="0" (
  echo [GOLD_V3_21] READY audit outputs written.
  echo [GOLD_V3_21] audit-only, not live approval.
) else (
  echo [GOLD_V3_21] BLOCKED or FAILED. script_exit_code=%EXIT_CODE%
)
goto END_HOLD

:FATAL_CD
echo [GOLD_V3_21] FATAL: could not move to repository root.
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_SCRIPT
echo [GOLD_V3_21] FATAL: runtime script not found.
echo [GOLD_V3_21] missing=%SCRIPT_PATH%
set "EXIT_CODE=1"
goto END_HOLD

:END_HOLD
echo.
echo ============================================================
echo [GOLD_V3_21] exit_code=%EXIT_CODE%
echo [GOLD_V3_21] Press any key to close this window.
echo ============================================================
pause
exit /b %EXIT_CODE%
