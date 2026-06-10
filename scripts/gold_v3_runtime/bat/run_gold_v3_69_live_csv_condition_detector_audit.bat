@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 69 live CSV condition detector audit-only runner.
REM Detects candidate conditions from closed live CSV rows only.
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
    echo [ERROR] Could not locate goldsharp_m15.csv.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE68_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\68_rank_dedup_selection_repro_audit_only"
set "STAGE51_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\51_full_candidate_virtual_opportunity_ledger_builder_audit_only"
set "STAGE50_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\69_live_csv_condition_detector_audit_only"
for %%I in ("%STAGE68_DIR%") do set "STAGE68_DIR=%%~fI"
for %%I in ("%STAGE51_DIR%") do set "STAGE51_DIR=%%~fI"
for %%I in ("%STAGE50_DIR%") do set "STAGE50_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%CANDLE_DIR%\goldsharp_m15.csv" (
    echo [ERROR] goldsharp_m15.csv not found.
    pause
    exit /b 1
)
if not exist "%CANDLE_DIR%\goldsharp_h4.csv" (
    echo [ERROR] goldsharp_h4.csv not found.
    pause
    exit /b 1
)
if not exist "%CANDLE_DIR%\goldsharp_m5.csv" (
    echo [ERROR] goldsharp_m5.csv not found.
    pause
    exit /b 1
)
if not exist "%STAGE68_DIR%\gold_v3_68_rank_dedup_selection_repro_summary.json" (
    echo [ERROR] Stage68 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE51_DIR%\gold_v3_51_virtual_opportunity_ledger.csv" (
    echo [ERROR] Stage51 virtual opportunity ledger not found.
    pause
    exit /b 1
)
if not exist "%STAGE50_DIR%\gold_v3_50_rolling_prior_60d_q70_state.csv" (
    echo [ERROR] Stage50 q70 state not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 69 LIVE CSV CONDITION DETECTOR AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE68_DIR=%STAGE68_DIR%
echo STAGE51_DIR=%STAGE51_DIR%
echo STAGE50_DIR=%STAGE50_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Detects candidate conditions from closed CSV only. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_69_live_csv_condition_detector_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage68-dir "%STAGE68_DIR%" ^
  --stage51-dir "%STAGE51_DIR%" ^
  --stage50-dir "%STAGE50_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 69 live CSV condition detector ended with errorlevel %ERR%.
    echo Paste this file if upload limit is reached:
    echo %OUTPUT_DIR%\gold_v3_69_PASTE_ME_LIVE_CSV_CONDITION_DETECTOR_SUMMARY.txt
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 69 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_69_PASTE_ME_LIVE_CSV_CONDITION_DETECTOR_SUMMARY.txt
echo.
pause
exit /b 0
