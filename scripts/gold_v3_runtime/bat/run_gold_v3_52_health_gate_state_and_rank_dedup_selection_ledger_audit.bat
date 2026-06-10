@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 52 health gate state and rank-dedup selection ledger audit-only runner.
REM Builds selection state ledgers only. Does not implement live trading.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\goldsharp_m15.csv" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\goldsharp_m15.csv" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\goldsharp_m15.csv" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\goldsharp_m15.csv" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Files directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE46_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\46_closed_asof_stage45_pool_contract_freeze_audit_only"
set "STAGE47_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\47_closed_asof_pool_contract_forward_audit_only"
set "STAGE49_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\49_closed_asof_state_schema_and_shadow_ledger_audit_only"
set "STAGE51_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\51_full_candidate_virtual_opportunity_ledger_builder_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\52_health_gate_state_rank_dedup_audit_only"
for %%I in ("%STAGE46_DIR%") do set "STAGE46_DIR=%%~fI"
for %%I in ("%STAGE47_DIR%") do set "STAGE47_DIR=%%~fI"
for %%I in ("%STAGE49_DIR%") do set "STAGE49_DIR=%%~fI"
for %%I in ("%STAGE51_DIR%") do set "STAGE51_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE46_DIR%\gold_v3_46_closed_asof_stage45_pool_contract.json" (
    echo [ERROR] Stage46 contract output not found.
    pause
    exit /b 1
)
if not exist "%STAGE47_DIR%\gold_v3_47_forward_audit_summary.json" (
    echo [ERROR] Stage47 output not found.
    pause
    exit /b 1
)
if not exist "%STAGE49_DIR%\gold_v3_49_state_schema_summary.json" (
    echo [ERROR] Stage49 output not found.
    pause
    exit /b 1
)
if not exist "%STAGE51_DIR%\gold_v3_51_virtual_opportunity_summary.json" (
    echo [ERROR] Stage51 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE51_DIR%\gold_v3_51_virtual_opportunity_ledger.csv" (
    echo [ERROR] Stage51 virtual opportunity ledger not found.
    pause
    exit /b 1
)
if not exist "%STAGE47_DIR%\stage47_replay\gold_v3_45_hv_sibling_strict_gate_trade_ledger.csv" (
    echo [ERROR] Stage47 strict gate trade ledger not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 52 HEALTH GATE SELECTION AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo This builds health gate state and rank-dedup selection ledger only. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_52_health_gate_state_and_rank_dedup_selection_ledger_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage46-dir "%STAGE46_DIR%" ^
  --stage47-dir "%STAGE47_DIR%" ^
  --stage49-dir "%STAGE49_DIR%" ^
  --stage51-dir "%STAGE51_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 52 health gate selection audit failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 52 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_52_PASTE_ME_HEALTH_GATE_SELECTION_SUMMARY.txt
echo.
pause
exit /b 0
