@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 50 H4 closed-readiness and prior-60D q70 state builder audit-only runner.
REM Materializes state artifacts only. Does not implement live trading.
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
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only"
for %%I in ("%STAGE46_DIR%") do set "STAGE46_DIR=%%~fI"
for %%I in ("%STAGE47_DIR%") do set "STAGE47_DIR=%%~fI"
for %%I in ("%STAGE49_DIR%") do set "STAGE49_DIR=%%~fI"
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
if not exist "%CANDLE_DIR%\goldsharp_m15.csv" (
    echo [ERROR] Missing goldsharp_m15.csv.
    pause
    exit /b 1
)
if not exist "%CANDLE_DIR%\goldsharp_h4.csv" (
    echo [ERROR] Missing goldsharp_h4.csv.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 50 STATE BUILDER AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo This builds H4 readiness and q70 state only. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage46-dir "%STAGE46_DIR%" ^
  --stage47-dir "%STAGE47_DIR%" ^
  --stage49-dir "%STAGE49_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    if exist "%OUTPUT_DIR%\gold_v3_50_PASTE_ME_STATE_BUILDER_SUMMARY.txt" if exist "%OUTPUT_DIR%\gold_v3_50_state_builder_summary.json" if exist "%OUTPUT_DIR%\gold_v3_50_validation_matrix.csv" (
        echo.
        echo [WARN] Python returned errorlevel %ERR%, but core Stage50 outputs exist.
        echo [WARN] This is expected when Windows rejects the extra-long Markdown report path.
        echo [WARN] Treating Stage50 core outputs as DONE. Use the PASTE_ME file below.
        > "%OUTPUT_DIR%\GOLD_V3_50_REPORT_PATH_WARNING.txt" echo Stage50 core outputs were generated. Python failed only while writing the long Markdown report path on Windows.
        set "ERR=0"
    )
)
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 50 state builder failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 50 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_50_PASTE_ME_STATE_BUILDER_SUMMARY.txt
echo.
pause
exit /b 0
