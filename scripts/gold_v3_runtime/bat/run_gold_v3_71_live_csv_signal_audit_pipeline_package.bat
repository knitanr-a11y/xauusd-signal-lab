@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 71 live CSV signal audit pipeline package.
REM Runs Stage69 -> Stage70 -> Stage71 in audit-only mode.
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

set "STAGE69_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\69_live_csv_condition_detector_audit_only"
set "STAGE70_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\70_live_csv_signal_decision_preview_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\71_live_csv_signal_audit_pipeline_package_audit_only"
for %%I in ("%STAGE69_DIR%") do set "STAGE69_DIR=%%~fI"
for %%I in ("%STAGE70_DIR%") do set "STAGE70_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

echo [GOLD V3 71 LIVE CSV SIGNAL AUDIT PIPELINE PACKAGE]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo.
echo This runs Stage69 -^> Stage70 -^> Stage71 in audit-only mode.
echo No MT5 orders, no Discord, no AI API, no live hook, no final signal.
echo.

call "%REPO_ROOT%\scripts\gold_v3_runtime\bat\run_gold_v3_69_live_csv_condition_detector_audit.bat"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo [ERROR] Stage69 failed or blocked. errorlevel=%ERR%
    pause
    exit /b %ERR%
)

call "%REPO_ROOT%\scripts\gold_v3_runtime\bat\run_gold_v3_70_live_csv_signal_decision_preview_audit.bat"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo [ERROR] Stage70 failed or blocked. errorlevel=%ERR%
    pause
    exit /b %ERR%
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_71_live_csv_signal_audit_pipeline_package.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage69-dir "%STAGE69_DIR%" ^
  --stage70-dir "%STAGE70_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 71 pipeline package ended with errorlevel %ERR%.
    echo Paste this file if upload limit is reached:
    echo %OUTPUT_DIR%\gold_v3_71_PASTE_ME_LIVE_CSV_SIGNAL_AUDIT_PIPELINE_PACKAGE_SUMMARY.txt
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 71 latest audit snapshot written to:
echo %OUTPUT_DIR%
echo.
echo Latest fixed snapshot files:
echo %OUTPUT_DIR%\gold_v3_71_latest_signal_snapshot.csv
echo %OUTPUT_DIR%\gold_v3_71_latest_signal_snapshot.json
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_71_PASTE_ME_LIVE_CSV_SIGNAL_AUDIT_PIPELINE_PACKAGE_SUMMARY.txt
echo.
pause
exit /b 0
