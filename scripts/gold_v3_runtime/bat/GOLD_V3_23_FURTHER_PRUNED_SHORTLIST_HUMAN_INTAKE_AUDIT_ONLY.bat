@echo off
setlocal EnableExtensions

rem GOLD V3 23 audit-only runner.
rem Builds a human intake packet from Stage22 outputs.

set "EXIT_CODE=1"

echo ============================================================
echo GOLD V3 23 FURTHER PRUNED HUMAN INTAKE - AUDIT ONLY
echo ============================================================
echo.

cd /d "%~dp0\..\..\.."
if errorlevel 1 goto FATAL_CD

set "REPO_ROOT=%CD%"
set "SCRIPT_PATH=scripts\gold_v3_runtime\gold_v3_23_further_pruned_shortlist_human_intake_audit_only.py"

echo [GOLD_V3_23] repo_root=%REPO_ROOT%
echo [GOLD_V3_23] script=%SCRIPT_PATH%
echo.

if not exist "%SCRIPT_PATH%" goto FATAL_SCRIPT

where py >nul 2>nul
if not errorlevel 1 goto RUN_PY

where python >nul 2>nul
if not errorlevel 1 goto RUN_PYTHON

echo [GOLD_V3_23] BLOCKED: Python launcher not found.
set "EXIT_CODE=1"
goto END_HOLD

:RUN_PY
echo [GOLD_V3_23] using py -3
py -3 "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:RUN_PYTHON
echo [GOLD_V3_23] using python
python "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:AFTER_RUN
echo.
if "%EXIT_CODE%"=="0" (
  echo [GOLD_V3_23] READY audit outputs written.
) else (
  echo [GOLD_V3_23] BLOCKED or FAILED. script_exit_code=%EXIT_CODE%
)
goto END_HOLD

:FATAL_CD
echo [GOLD_V3_23] FATAL: could not move to repository root.
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_SCRIPT
echo [GOLD_V3_23] FATAL: runtime script not found.
echo [GOLD_V3_23] missing=%SCRIPT_PATH%
set "EXIT_CODE=1"
goto END_HOLD

:END_HOLD
echo.
echo ============================================================
echo [GOLD_V3_23] exit_code=%EXIT_CODE%
echo [GOLD_V3_23] Press any key to close this window.
echo ============================================================
pause
exit /b %EXIT_CODE%
