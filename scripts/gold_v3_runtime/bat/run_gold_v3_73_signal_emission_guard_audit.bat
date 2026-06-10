@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 73 signal emission guard audit-only.
REM Reads Stage72 latest snapshot and decides NO_ACTION / ALLOW_AUDIT_SIGNAL_EVENT / SUPPRESS_DUPLICATE_SIGNAL.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\72_live_csv_update_monitor_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\72_live_csv_update_monitor_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\72_live_csv_update_monitor_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\72_live_csv_update_monitor_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage72 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE72_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\72_live_csv_update_monitor_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\73_signal_emission_guard_audit_only"
for %%I in ("%STAGE72_DIR%") do set "STAGE72_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE72_DIR%\gold_v3_72_live_csv_update_monitor_summary.json" (
    echo [ERROR] Stage72 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE72_DIR%\gold_v3_72_latest_pipeline_snapshot.json" (
    echo [ERROR] Stage72 latest pipeline snapshot not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 73 SIGNAL EMISSION GUARD AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE72_DIR=%STAGE72_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Audit-only emission guard. No Discord, no MT5, no AI API, no final signal.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_73_signal_emission_guard_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage72-dir "%STAGE72_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 73 signal emission guard ended with errorlevel %ERR%.
    echo Paste this file if upload limit is reached:
    echo %OUTPUT_DIR%\gold_v3_73_PASTE_ME_SIGNAL_EMISSION_GUARD_SUMMARY.txt
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 73 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_73_PASTE_ME_SIGNAL_EMISSION_GUARD_SUMMARY.txt
echo.
pause
exit /b 0
