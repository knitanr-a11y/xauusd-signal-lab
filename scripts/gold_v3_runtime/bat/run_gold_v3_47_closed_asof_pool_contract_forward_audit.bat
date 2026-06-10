@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 47 closed-asof pool contract forward audit-only runner.
REM Reuses Stage46 frozen contract. Does not change candidate pool.
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
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\47_closed_asof_pool_contract_forward_audit_only"
for %%I in ("%STAGE46_DIR%") do set "STAGE46_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE46_DIR%\gold_v3_46_closed_asof_stage45_pool_contract.json" (
    echo [ERROR] Stage46 contract output not found:
    echo %STAGE46_DIR%\gold_v3_46_closed_asof_stage45_pool_contract.json
    echo Run Stage46 BAT first.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 47 FORWARD AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE46_DIR=%STAGE46_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo This is audit-only. Contract is reused. No candidate changes.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_47_closed_asof_pool_contract_forward_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage46-dir "%STAGE46_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 47 forward audit failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 47 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_47_PASTE_ME_FORWARD_AUDIT_SUMMARY.txt
echo.
pause
exit /b 0
