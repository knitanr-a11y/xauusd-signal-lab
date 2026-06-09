@echo off
setlocal EnableExtensions

rem GOLD V3 20 loss feature pruning PF uplift audit-only runner.
rem This BAT runs an audit-only script. Daily cap is not used.
rem No production or external actions are enabled by this BAT.

set "EXIT_CODE=1"

echo ============================================================
echo GOLD V3 20 LOSS FEATURE PRUNING PF UPLIFT - AUDIT ONLY
echo ============================================================
echo.

cd /d "%~dp0\..\..\.."
if errorlevel 1 goto FATAL_CD

set "REPO_ROOT=%CD%"
set "SCRIPT_PATH=scripts\gold_v3_runtime\gold_v3_20_loss_feature_pruning_pf_uplift_audit_only.py"

echo [GOLD_V3_20] repo_root=%REPO_ROOT%
echo [GOLD_V3_20] script=%SCRIPT_PATH%
echo [GOLD_V3_20] scope: entry-pre-known feature pruning only; no daily cap.
echo.

if not exist "%SCRIPT_PATH%" goto FATAL_SCRIPT

where py >nul 2>nul
if not errorlevel 1 goto RUN_PY

where python >nul 2>nul
if not errorlevel 1 goto RUN_PYTHON

echo [GOLD_V3_20] BLOCKED: Python launcher not found.
set "EXIT_CODE=1"
goto END_HOLD

:RUN_PY
echo [GOLD_V3_20] using py -3
py -3 "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:RUN_PYTHON
echo [GOLD_V3_20] using python
python "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:AFTER_RUN
echo.
if "%EXIT_CODE%"=="0" (
  echo [GOLD_V3_20] READY audit outputs written.
  echo [GOLD_V3_20] audit-only, not live approval.
) else (
  echo [GOLD_V3_20] BLOCKED or FAILED. script_exit_code=%EXIT_CODE%
)
goto END_HOLD

:FATAL_CD
echo [GOLD_V3_20] FATAL: could not move to repository root.
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_SCRIPT
echo [GOLD_V3_20] FATAL: runtime script not found.
echo [GOLD_V3_20] missing=%SCRIPT_PATH%
set "EXIT_CODE=1"
goto END_HOLD

:END_HOLD
echo.
echo ============================================================
echo [GOLD_V3_20] exit_code=%EXIT_CODE%
echo [GOLD_V3_20] Press any key to close this window.
echo ============================================================
pause
exit /b %EXIT_CODE%
