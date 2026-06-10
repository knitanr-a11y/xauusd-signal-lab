@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 46 closed-asof Stage45 pool contract freeze audit-only runner.
REM This validates and freezes the Stage45 closed-asof full candidate pool contract.
REM It does NOT run MT5 orders, Discord, AI API, live hook, or final signals.

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

set "STAGE45_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\45_high_vol_sibling_strict_gate_walkforward_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\46_closed_asof_stage45_pool_contract_freeze_audit_only"
for %%I in ("%STAGE45_DIR%") do set "STAGE45_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE45_DIR%\gold_v3_45_hv_sibling_strict_gate_summary.json" (
    echo [ERROR] Stage45 closed output not found:
    echo %STAGE45_DIR%\gold_v3_45_hv_sibling_strict_gate_summary.json
    echo Run Stage45 closed BAT first.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 46 CONTRACT FREEZE AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo STAGE45_DIR=%STAGE45_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo This is audit-only. Candidate pool is retained. No manual demotion/removal.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_46_closed_asof_stage45_pool_contract_freeze_audit.py" ^
  --stage45-dir "%STAGE45_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 46 contract freeze audit failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 46 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if needed:
echo %OUTPUT_DIR%\gold_v3_46_PASTE_ME_CONTRACT_FREEZE_SUMMARY.txt
echo.
pause
exit /b 0
