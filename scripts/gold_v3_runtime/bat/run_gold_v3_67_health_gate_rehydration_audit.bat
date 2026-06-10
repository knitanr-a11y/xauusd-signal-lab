@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 67 health gate rehydration audit-only runner.
REM Rehydrates rolling health gate state from audited GOLD V3 outcomes.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\66_virtual_monitoring_state_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\66_virtual_monitoring_state_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\66_virtual_monitoring_state_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\66_virtual_monitoring_state_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage66 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE66_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\66_virtual_monitoring_state_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\67_health_gate_rehydration_audit_only"
for %%I in ("%STAGE66_DIR%") do set "STAGE66_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE66_DIR%\gold_v3_66_virtual_monitoring_summary.json" (
    echo [ERROR] Stage66 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE66_DIR%\gold_v3_66_virtual_opportunity_q70_joined_ledger.csv" (
    echo [ERROR] Stage66 joined ledger not found.
    pause
    exit /b 1
)
if not exist "%STAGE66_DIR%\gold_v3_66_candidate_virtual_monitoring_state.csv" (
    echo [ERROR] Stage66 candidate state not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 67 HEALTH GATE REHYDRATION AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE66_DIR=%STAGE66_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Rehydrates rolling health gate state only. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_67_health_gate_rehydration_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage66-dir "%STAGE66_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 67 health gate rehydration ended with errorlevel %ERR%.
    echo This can be expected if no acceptable audited outcome source or exact candidate_key match exists.
    echo Paste this file if upload limit is reached:
    echo %OUTPUT_DIR%\gold_v3_67_PASTE_ME_HEALTH_GATE_REHYDRATION_SUMMARY.txt
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 67 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_67_PASTE_ME_HEALTH_GATE_REHYDRATION_SUMMARY.txt
echo.
pause
exit /b 0
