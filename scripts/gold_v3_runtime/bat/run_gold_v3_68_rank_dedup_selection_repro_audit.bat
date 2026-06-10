@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 68 rank/dedup selection reproduction audit-only runner.
REM Reproduces selection from Stage67 health gate events.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\67_health_gate_rehydration_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\67_health_gate_rehydration_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\67_health_gate_rehydration_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\67_health_gate_rehydration_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage67 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE67_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\67_health_gate_rehydration_audit_only"
set "STAGE66_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\66_virtual_monitoring_state_audit_only"
set "STAGE52_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\52_health_gate_state_rank_dedup_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\68_rank_dedup_selection_repro_audit_only"
for %%I in ("%STAGE67_DIR%") do set "STAGE67_DIR=%%~fI"
for %%I in ("%STAGE66_DIR%") do set "STAGE66_DIR=%%~fI"
for %%I in ("%STAGE52_DIR%") do set "STAGE52_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE67_DIR%\gold_v3_67_health_gate_rehydration_summary.json" (
    echo [ERROR] Stage67 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE67_DIR%\gold_v3_67_health_gate_event_ledger.csv" (
    echo [ERROR] Stage67 event ledger not found.
    pause
    exit /b 1
)
if not exist "%STAGE66_DIR%\gold_v3_66_virtual_opportunity_q70_joined_ledger.csv" (
    echo [ERROR] Stage66 joined ledger not found.
    pause
    exit /b 1
)
if not exist "%STAGE52_DIR%\gold_v3_52_selected_trade_ledger.csv" (
    echo [ERROR] Stage52 selected trade ledger not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 68 RANK DEDUP SELECTION REPRO AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE67_DIR=%STAGE67_DIR%
echo STAGE66_DIR=%STAGE66_DIR%
echo STAGE52_DIR=%STAGE52_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Reproduces rank/dedup selection only. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_68_rank_dedup_selection_repro_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage67-dir "%STAGE67_DIR%" ^
  --stage66-dir "%STAGE66_DIR%" ^
  --stage52-dir "%STAGE52_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 68 rank/dedup selection repro ended with errorlevel %ERR%.
    echo Paste this file if upload limit is reached:
    echo %OUTPUT_DIR%\gold_v3_68_PASTE_ME_RANK_DEDUP_SELECTION_REPRO_SUMMARY.txt
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 68 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_68_PASTE_ME_RANK_DEDUP_SELECTION_REPRO_SUMMARY.txt
echo.
pause
exit /b 0
