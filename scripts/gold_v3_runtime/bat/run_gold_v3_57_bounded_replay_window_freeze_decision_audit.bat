@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 57 bounded replay window freeze decision audit-only runner.
REM Records human decision B only. Does not implement live trading.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\56_mutable_source_candle_append_only_drift_policy_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\56_mutable_source_candle_append_only_drift_policy_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\56_mutable_source_candle_append_only_drift_policy_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\56_mutable_source_candle_append_only_drift_policy_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage56 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE54_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\54_restart_replay_checkpoint_state_audit_only"
set "STAGE55_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\55_replay_from_checkpoint_dry_run_audit_only"
set "STAGE56_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\56_mutable_source_candle_append_only_drift_policy_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\57_bounded_replay_window_freeze_decision_audit_only"
for %%I in ("%STAGE54_DIR%") do set "STAGE54_DIR=%%~fI"
for %%I in ("%STAGE55_DIR%") do set "STAGE55_DIR=%%~fI"
for %%I in ("%STAGE56_DIR%") do set "STAGE56_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE54_DIR%\gold_v3_54_checkpoint_summary.json" (
    echo [ERROR] Stage54 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE55_DIR%\gold_v3_55_replay_dry_run_summary.json" (
    echo [ERROR] Stage55 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE56_DIR%\gold_v3_56_policy_summary.json" (
    echo [ERROR] Stage56 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE56_DIR%\gold_v3_56_drift_policy_matrix.csv" (
    echo [ERROR] Stage56 drift policy matrix not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 57 BOUNDED REPLAY WINDOW FREEZE DECISION AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE54_DIR=%STAGE54_DIR%
echo STAGE55_DIR=%STAGE55_DIR%
echo STAGE56_DIR=%STAGE56_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Human decision: B_BOUNDED_REPLAY_WINDOW_FREEZE.
echo This records the bounded replay contract only. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_57_bounded_replay_window_freeze_decision_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage54-dir "%STAGE54_DIR%" ^
  --stage55-dir "%STAGE55_DIR%" ^
  --stage56-dir "%STAGE56_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 57 bounded replay window freeze decision audit failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 57 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_57_PASTE_ME_BOUNDED_REPLAY_SUMMARY.txt
echo.
pause
exit /b 0
