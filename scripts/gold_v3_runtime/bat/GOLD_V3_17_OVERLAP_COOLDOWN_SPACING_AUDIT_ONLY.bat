@echo off
setlocal EnableExtensions

rem GOLD V3 17 overlap cooldown spacing audit-only runner.
rem Runtime BAT location: scripts\gold_v3_runtime\bat\
rem This BAT audits all Stage 16 candidates including rank 7/8 weak h1_atr56 comparison profiles.
rem It must not approve final candidates, finalize thresholds, train models, generate signals, create ZIP output,
rem call AI APIs, notify Discord, place MT5 orders, or enable live hooks/evaluators/final signals.

set "EXIT_CODE=1"

echo ============================================================
echo GOLD V3 17 OVERLAP COOLDOWN SPACING - AUDIT ONLY
echo Runtime BAT: scripts\gold_v3_runtime\bat\GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_AUDIT_ONLY.bat
echo ============================================================
echo.

cd /d "%~dp0\..\..\.."
if errorlevel 1 goto FATAL_CD

set "REPO_ROOT=%CD%"
set "SCRIPT_PATH=scripts\gold_v3_runtime\gold_v3_17_overlap_cooldown_spacing_audit_only.py"

echo [GOLD_V3_17] repo_root=%REPO_ROOT%
echo [GOLD_V3_17] script=%SCRIPT_PATH%
echo [GOLD_V3_17] expected input: Stage 15 READY ledger and Stage 16 READY all-candidate review
echo [GOLD_V3_17] scope: overlap/cooldown/spacing across all ranks 1/2/3/4/6/7/8
echo [GOLD_V3_17] forbidden: final approval/threshold/training/signal/ZIP/AI/Discord/MT5/live/final signal
echo.

if not exist "%SCRIPT_PATH%" goto FATAL_SCRIPT

where py >nul 2>nul
if not errorlevel 1 goto RUN_PY

where python >nul 2>nul
if not errorlevel 1 goto RUN_PYTHON

echo [GOLD_V3_17] BLOCKED: Python launcher not found.
set "EXIT_CODE=1"
goto END_HOLD

:RUN_PY
echo [GOLD_V3_17] using py -3
py -3 "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:RUN_PYTHON
echo [GOLD_V3_17] using python
python "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:AFTER_RUN
echo.
if "%EXIT_CODE%"=="0" (
  echo [GOLD_V3_17] READY overlap/cooldown/spacing outputs written.
  echo [GOLD_V3_17] This is NOT final approval and NOT live approval.
) else (
  echo [GOLD_V3_17] BLOCKED or FAILED. script_exit_code=%EXIT_CODE%
)
goto END_HOLD

:FATAL_CD
echo [GOLD_V3_17] FATAL: could not move to repository root.
echo [GOLD_V3_17] bat_dir=%~dp0
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_SCRIPT
echo [GOLD_V3_17] FATAL: runtime script not found.
echo [GOLD_V3_17] missing=%SCRIPT_PATH%
set "EXIT_CODE=1"
goto END_HOLD

:END_HOLD
echo.
echo ============================================================
echo [GOLD_V3_17] exit_code=%EXIT_CODE%
echo [GOLD_V3_17] Press any key to close this window.
echo ============================================================
pause
exit /b %EXIT_CODE%
