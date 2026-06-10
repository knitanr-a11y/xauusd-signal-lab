@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 54 restart/replay checkpoint state audit-only runner.
REM Builds checkpoint state only. Does not implement live trading.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Files directory with FX_OUTPUTS\gold_v3.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\54_restart_replay_checkpoint_state_audit_only"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%CANDLE_DIR%\FX_OUTPUTS\gold_v3\49_closed_asof_state_schema_and_shadow_ledger_audit_only\gold_v3_49_state_schema_summary.json" (
    echo [ERROR] Stage49 summary not found.
    pause
    exit /b 1
)
if not exist "%CANDLE_DIR%\FX_OUTPUTS\gold_v3\50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only\gold_v3_50_state_builder_summary.json" (
    echo [ERROR] Stage50 summary not found.
    pause
    exit /b 1
)
if not exist "%CANDLE_DIR%\FX_OUTPUTS\gold_v3\51_full_candidate_virtual_opportunity_ledger_builder_audit_only\gold_v3_51_virtual_opportunity_summary.json" (
    echo [ERROR] Stage51 summary not found.
    pause
    exit /b 1
)
if not exist "%CANDLE_DIR%\FX_OUTPUTS\gold_v3\52_health_gate_state_rank_dedup_audit_only\gold_v3_52_health_gate_selection_summary.json" (
    echo [ERROR] Stage52 summary not found.
    pause
    exit /b 1
)
if not exist "%CANDLE_DIR%\FX_OUTPUTS\gold_v3\53_pending_to_closed_shadow_trade_adjudication_audit_only\gold_v3_53_shadow_adjudication_summary.json" (
    echo [ERROR] Stage53 summary not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 54 RESTART REPLAY CHECKPOINT AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo This builds restart/replay checkpoint state only. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_54_restart_replay_checkpoint_state_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 54 restart/replay checkpoint audit failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 54 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_54_PASTE_ME_CHECKPOINT_SUMMARY.txt
echo.
pause
exit /b 0
