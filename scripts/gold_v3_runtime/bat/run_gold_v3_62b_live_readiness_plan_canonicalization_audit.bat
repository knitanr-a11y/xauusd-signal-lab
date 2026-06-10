@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 62B live-readiness plan canonicalization audit-only runner.
REM Canonicalizes Stage62 plan. No live enablement.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\62_live_readiness_implementation_planning_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\62_live_readiness_implementation_planning_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\62_live_readiness_implementation_planning_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\62_live_readiness_implementation_planning_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage62 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE62_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\62_live_readiness_implementation_planning_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\62b_live_readiness_plan_canonicalization_audit_only"
for %%I in ("%STAGE62_DIR%") do set "STAGE62_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE62_DIR%\gold_v3_62_live_readiness_planning_summary.json" (
    echo [ERROR] Stage62 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE62_DIR%\gold_v3_62_gap_to_plan_matrix.csv" (
    echo [ERROR] Stage62 gap-to-plan matrix not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 62B LIVE READINESS PLAN CANONICALIZATION AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE62_DIR=%STAGE62_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Canonicalizes Stage62 plan. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_62b_live_readiness_plan_canonicalization_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage62-dir "%STAGE62_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 62B canonicalization failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 62B outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_62b_PASTE_ME_CANONICAL_PLAN_SUMMARY.txt
echo.
pause
exit /b 0
