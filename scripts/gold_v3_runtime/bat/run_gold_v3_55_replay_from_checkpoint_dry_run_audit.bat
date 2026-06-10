@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 55 replay-from-checkpoint dry run audit-only runner.
REM Verifies checkpoint hashes/counts/anchors only. Does not implement live trading.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\54_restart_replay_checkpoint_state_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\54_restart_replay_checkpoint_state_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\54_restart_replay_checkpoint_state_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\54_restart_replay_checkpoint_state_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage54 checkpoint directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE54_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\54_restart_replay_checkpoint_state_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\55_replay_from_checkpoint_dry_run_audit_only"
for %%I in ("%STAGE54_DIR%") do set "STAGE54_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE54_DIR%\gold_v3_54_checkpoint_summary.json" (
    echo [ERROR] Stage54 checkpoint summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE54_DIR%\gold_v3_54_source_artifact_hashes.csv" (
    echo [ERROR] Stage54 artifact hashes not found.
    pause
    exit /b 1
)
if not exist "%STAGE54_DIR%\gold_v3_54_restart_plan.csv" (
    echo [ERROR] Stage54 restart plan not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 55 REPLAY FROM CHECKPOINT DRY RUN AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE54_DIR=%STAGE54_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo This verifies checkpoint hashes/counts/anchors only. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_55_replay_from_checkpoint_dry_run_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage54-dir "%STAGE54_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 55 replay checkpoint dry run failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 55 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_55_PASTE_ME_REPLAY_DRY_RUN_SUMMARY.txt
echo.
pause
exit /b 0
