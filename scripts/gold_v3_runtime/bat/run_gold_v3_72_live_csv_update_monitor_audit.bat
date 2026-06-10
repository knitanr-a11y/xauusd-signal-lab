@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 72 live CSV update monitor audit-only.
REM Keeps a console open and runs Stage69 -> Stage70 -> Stage71 when goldsharp_m15.csv latest closed time changes.
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

set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\72_live_csv_update_monitor_audit_only"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 72 LIVE CSV UPDATE MONITOR AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo This window will stay open and monitor goldsharp_m15.csv.
echo It runs Stage69 -^> Stage70 -^> Stage71 only when latest closed M15 time changes.
echo No MT5 orders, no Discord, no AI API, no live hook, no final signal.
echo.
echo To stop monitoring, close this window or press Ctrl+C.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_72_live_csv_update_monitor_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --output-dir "%OUTPUT_DIR%" ^
  --poll-seconds 30

set "ERR=%ERRORLEVEL%"
echo.
echo [STOPPED] GOLD V3 72 monitor exited with errorlevel %ERR%.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_72_PASTE_ME_LIVE_CSV_UPDATE_MONITOR_SUMMARY.txt
echo.
pause
exit /b %ERR%
