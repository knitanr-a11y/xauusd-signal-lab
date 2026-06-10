@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 62 live-readiness implementation planning audit-only runner.
REM Planning only. No live enablement.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\61_frozen_audit_package_human_review_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\61_frozen_audit_package_human_review_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\61_frozen_audit_package_human_review_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\61_frozen_audit_package_human_review_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage61 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE61_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\61_frozen_audit_package_human_review_audit_only"
set "STAGE48_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\48_closed_asof_pool_contract_live_readiness_gap_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\62_live_readiness_implementation_planning_audit_only"
for %%I in ("%STAGE61_DIR%") do set "STAGE61_DIR=%%~fI"
for %%I in ("%STAGE48_DIR%") do set "STAGE48_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE61_DIR%\gold_v3_61_frozen_audit_package_summary.json" (
    echo [ERROR] Stage61 summary not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 62 LIVE READINESS IMPLEMENTATION PLANNING AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE48_DIR=%STAGE48_DIR%
echo STAGE61_DIR=%STAGE61_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Planning only. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_62_live_readiness_implementation_planning_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage48-dir "%STAGE48_DIR%" ^
  --stage61-dir "%STAGE61_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 62 live-readiness planning failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 62 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_62_PASTE_ME_LIVE_READINESS_PLANNING_SUMMARY.txt
echo.
pause
exit /b 0
