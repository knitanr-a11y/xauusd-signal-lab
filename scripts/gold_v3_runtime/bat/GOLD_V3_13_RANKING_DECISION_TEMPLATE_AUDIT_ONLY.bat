@echo off
setlocal EnableExtensions

rem GOLD V3 13 ranking decision template audit-only runner.
rem Runtime BAT location: scripts\gold_v3_runtime\bat\
rem This BAT only creates the stage-13 audit template from existing stage-12 outputs.
rem It must not approve, replay, train, signal, zip, call AI APIs, notify Discord,
rem place MT5 orders, or enable live hooks/evaluators.
rem The console is intentionally held open so errors remain visible.

set "EXIT_CODE=1"

echo ============================================================
echo GOLD V3 13 RANKING DECISION TEMPLATE - AUDIT ONLY
echo Runtime BAT: scripts\gold_v3_runtime\bat\GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY.bat
echo This window will NOT close until you press a key.
echo ============================================================
echo.

cd /d "%~dp0..\..\.."
if errorlevel 1 goto FATAL_CD

set "REPO_ROOT=%CD%"
set "INPUT_DIR=%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\12_deployability_review_packet_audit_only"
set "OUTPUT_DIR=%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\13_ranking_decision_template_audit_only"
set "SCRIPT_PATH=scripts\gold_v3_runtime\gold_v3_13_ranking_decision_template_audit_only.py"

echo [GOLD_V3_13] repo_root=%REPO_ROOT%
echo [GOLD_V3_13] input_dir=%INPUT_DIR%
echo [GOLD_V3_13] output_dir=%OUTPUT_DIR%
echo [GOLD_V3_13] script=%SCRIPT_PATH%
echo [GOLD_V3_13] forbidden: approval/replay/training/signal/ZIP/AI/Discord/MT5/live/final approval
echo.

echo [GOLD_V3_13] creating output folder...
mkdir "%OUTPUT_DIR%" 2>nul
if not exist "%OUTPUT_DIR%\" goto FATAL_OUTPUT_DIR
echo [GOLD_V3_13] output folder exists.
echo [GOLD_V3_13] BAT started. > "%OUTPUT_DIR%\gold_v3_13_bat_started.txt"
echo [GOLD_V3_13] repo_root=%REPO_ROOT% >> "%OUTPUT_DIR%\gold_v3_13_bat_started.txt"
echo [GOLD_V3_13] input_dir=%INPUT_DIR% >> "%OUTPUT_DIR%\gold_v3_13_bat_started.txt"
echo [GOLD_V3_13] output_dir=%OUTPUT_DIR% >> "%OUTPUT_DIR%\gold_v3_13_bat_started.txt"
echo.

echo [GOLD_V3_13] checking required stage12 files...
if exist "%INPUT_DIR%\gold_v3_12_summary.json" (
  echo [GOLD_V3_13] FOUND   gold_v3_12_summary.json
) else (
  echo [GOLD_V3_13] MISSING gold_v3_12_summary.json
)
if exist "%INPUT_DIR%\gold_v3_12_deployability_review_packet.csv" (
  echo [GOLD_V3_13] FOUND   gold_v3_12_deployability_review_packet.csv
) else (
  echo [GOLD_V3_13] MISSING gold_v3_12_deployability_review_packet.csv
)
if exist "%INPUT_DIR%\gold_v3_12_deferred_candidate_diagnostics.csv" (
  echo [GOLD_V3_13] FOUND   gold_v3_12_deferred_candidate_diagnostics.csv
) else (
  echo [GOLD_V3_13] MISSING gold_v3_12_deferred_candidate_diagnostics.csv
)
echo.

if not exist "%SCRIPT_PATH%" goto FATAL_SCRIPT

where py >nul 2>nul
if not errorlevel 1 goto RUN_PY

where python >nul 2>nul
if not errorlevel 1 goto RUN_PYTHON

echo [GOLD_V3_13] BLOCKED: Python launcher not found.
echo [GOLD_V3_13] BLOCKED: Python launcher not found. > "%OUTPUT_DIR%\gold_v3_13_bat_blocked_no_python.txt"
set "EXIT_CODE=1"
goto END_HOLD

:RUN_PY
echo [GOLD_V3_13] using py -3
py -3 "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:RUN_PYTHON
echo [GOLD_V3_13] using python
python "%SCRIPT_PATH%" --repo-root "%REPO_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
goto AFTER_RUN

:AFTER_RUN
echo [GOLD_V3_13] script_exit_code=%EXIT_CODE% > "%OUTPUT_DIR%\gold_v3_13_bat_exit_code.txt"
if not "%EXIT_CODE%"=="0" goto BLOCKED_OR_FAILED

echo.
echo [GOLD_V3_13] READY audit-only.
echo [GOLD_V3_13] Check: %OUTPUT_DIR%\gold_v3_13_summary.json
goto END_HOLD

:BLOCKED_OR_FAILED
echo.
echo [GOLD_V3_13] BLOCKED or FAILED.
echo [GOLD_V3_13] script_exit_code=%EXIT_CODE%
echo [GOLD_V3_13] Check: %OUTPUT_DIR%\gold_v3_13_summary.json
echo [GOLD_V3_13] Check: %OUTPUT_DIR%\gold_v3_13_exception.txt
goto END_HOLD

:FATAL_CD
echo [GOLD_V3_13] FATAL: could not move to repository root.
echo [GOLD_V3_13] bat_dir=%~dp0
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_OUTPUT_DIR
echo [GOLD_V3_13] FATAL: output folder was NOT created.
echo [GOLD_V3_13] output_dir=%OUTPUT_DIR%
set "EXIT_CODE=1"
goto END_HOLD

:FATAL_SCRIPT
echo [GOLD_V3_13] FATAL: runtime script not found.
echo [GOLD_V3_13] missing=%SCRIPT_PATH%
set "EXIT_CODE=1"
goto END_HOLD

:END_HOLD
echo.
echo ============================================================
echo [GOLD_V3_13] exit_code=%EXIT_CODE%
echo [GOLD_V3_13] Press any key to close this window.
echo ============================================================
pause
exit /b %EXIT_CODE%
