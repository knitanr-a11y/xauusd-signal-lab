@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 70 live CSV signal decision preview audit-only runner.
REM Produces SIGNAL/NO_SIGNAL preview from latest closed condition candidates.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\69_live_csv_condition_detector_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\69_live_csv_condition_detector_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\69_live_csv_condition_detector_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\69_live_csv_condition_detector_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage69 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE69_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\69_live_csv_condition_detector_audit_only"
set "STAGE68_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\68_rank_dedup_selection_repro_audit_only"
set "STAGE67_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\67_health_gate_rehydration_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\70_live_csv_signal_decision_preview_audit_only"
for %%I in ("%STAGE69_DIR%") do set "STAGE69_DIR=%%~fI"
for %%I in ("%STAGE68_DIR%") do set "STAGE68_DIR=%%~fI"
for %%I in ("%STAGE67_DIR%") do set "STAGE67_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE69_DIR%\gold_v3_69_live_csv_condition_detector_summary.json" (
    echo [ERROR] Stage69 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE69_DIR%\gold_v3_69_latest_closed_condition_candidates.csv" (
    echo [ERROR] Stage69 latest closed condition candidates not found.
    pause
    exit /b 1
)
if not exist "%STAGE68_DIR%\gold_v3_68_rank_dedup_selection_repro_summary.json" (
    echo [ERROR] Stage68 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE67_DIR%\gold_v3_67_health_gate_rehydrated_candidate_state.csv" (
    echo [ERROR] Stage67 candidate state not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 70 LIVE CSV SIGNAL DECISION PREVIEW AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE69_DIR=%STAGE69_DIR%
echo STAGE68_DIR=%STAGE68_DIR%
echo STAGE67_DIR=%STAGE67_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Produces audit-only SIGNAL/NO_SIGNAL preview. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_70_live_csv_signal_decision_preview_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage69-dir "%STAGE69_DIR%" ^
  --stage68-dir "%STAGE68_DIR%" ^
  --stage67-dir "%STAGE67_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 70 signal decision preview ended with errorlevel %ERR%.
    echo Paste this file if upload limit is reached:
    echo %OUTPUT_DIR%\gold_v3_70_PASTE_ME_LIVE_CSV_SIGNAL_DECISION_PREVIEW_SUMMARY.txt
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 70 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_70_PASTE_ME_LIVE_CSV_SIGNAL_DECISION_PREVIEW_SUMMARY.txt
echo.
pause
exit /b 0
