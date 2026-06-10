@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 80 immutable runtime monitor audit-only.
REM Every minute + 5 seconds, detects new closed M15 CSV row.
REM On new M15: Stage76 --once -> Stage79 immutable snapshot.
REM No Discord send, no MT5 order, no AI API, no live hook, no final signal.

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
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Files directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\80_immutable_runtime_monitor_audit_only"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 80 IMMUTABLE RUNTIME MONITOR AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Schedule: every minute at second 05.
echo On new M15: Stage76 --once then Stage79 immutable snapshot.
echo Evidence snapshots go under: FX_OUTPUTS\gold_v3\79i\YYYYMMDD\RUN_ID
echo No MT5 orders, no Discord, no AI API, no live hook, no final signal.
echo.
echo To stop monitoring, close this window or press Ctrl+C.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_80_immutable_runtime_monitor_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --output-dir "%OUTPUT_DIR%" ^
  --minute-lag-seconds 5

set "ERR=%ERRORLEVEL%"
echo.
echo [STOPPED] GOLD V3 80 immutable runtime monitor exited with errorlevel %ERR%.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt
echo.
pause
exit /b %ERR%
