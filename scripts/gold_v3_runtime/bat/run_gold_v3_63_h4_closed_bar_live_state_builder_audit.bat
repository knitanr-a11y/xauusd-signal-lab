@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 63 H4 closed-bar live state builder audit-only runner.
REM CSV contract: open/in-progress candles are not written to CSV.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\62b_live_readiness_plan_canonicalization_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\62b_live_readiness_plan_canonicalization_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\62b_live_readiness_plan_canonicalization_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\62b_live_readiness_plan_canonicalization_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage62B output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE62B_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\62b_live_readiness_plan_canonicalization_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\63_h4_closed_bar_live_state_builder_audit_only"
for %%I in ("%STAGE62B_DIR%") do set "STAGE62B_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE62B_DIR%\gold_v3_62b_plan_canonicalization_summary.json" (
    echo [ERROR] Stage62B summary not found.
    pause
    exit /b 1
)
if not exist "%CANDLE_DIR%\goldsharp_h4.csv" (
    echo [ERROR] goldsharp_h4.csv not found in CANDLE_DIR.
    echo CANDLE_DIR=%CANDLE_DIR%
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 63 H4 CLOSED BAR LIVE STATE BUILDER AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE62B_DIR=%STAGE62B_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo CSV contract: open/in-progress candles are not written to CSV.
echo Latest H4 CSV row is treated as closed by CSV contract.
echo No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_63_h4_closed_bar_live_state_builder_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage62b-dir "%STAGE62B_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 63 H4 closed-bar state builder failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 63 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_63_PASTE_ME_H4_CLOSED_BAR_STATE_SUMMARY.txt
echo.
pause
exit /b 0
