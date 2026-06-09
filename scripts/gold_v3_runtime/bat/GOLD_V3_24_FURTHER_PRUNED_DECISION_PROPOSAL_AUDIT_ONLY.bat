@echo off
setlocal EnableExtensions

rem GOLD V3 24 compact proposal runner.

set "EXIT_CODE=1"

echo ============================================================
echo GOLD V3 24 FURTHER PRUNED PROPOSAL
echo ============================================================
echo.

cd /d "%~dp0\..\..\.."
if errorlevel 1 goto FATAL_CD

set "REPO_ROOT=%CD%"
set "SCRIPT_PATH=scripts\gold_v3_runtime\gold_v3_24_further_pruned_decision_proposal_audit_only.py"

echo [GOLD_V3_24] repo_root=%REPO_ROOT%
echo [GOLD_V3_24] script=%SCRIPT_PATH%
echo.

if not exist "%SCRIPT_PATH%" goto FATAL_SCRIPT

where py >nul 2>nul
if not errorlevel 1 goto RUN_PY

where python >nul 2>nul
if not errorlevel 1 goto RUN_PYTHON

echo [GOLD_V3_24] Python not found.
set "EXIT_CODE=1"
goto END_HOLD

:RUN_PY
py -3 "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:RUN_PYTHON
python "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:AFTER_RUN
echo.
echo [GOLD_V3_24] exit_code=%EXIT_CODE%
goto END_HOLD

:FATAL_CD
echo [GOLD_V3_24] FATAL: could not move to repository root.
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_SCRIPT
echo [GOLD_V3_24] FATAL: runtime script not found.
echo [GOLD_V3_24] missing=%SCRIPT_PATH%
set "EXIT_CODE=1"
goto END_HOLD

:END_HOLD
echo.
echo Press any key to close.
pause
exit /b %EXIT_CODE%
