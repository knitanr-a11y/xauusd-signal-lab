@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 75 external action payload preview audit-only.
REM Builds suppressed/preview-only Discord and MT5 payloads from Stage74.
REM No Discord send, no MT5 order, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\74_guarded_live_csv_monitor_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\74_guarded_live_csv_monitor_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\74_guarded_live_csv_monitor_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\74_guarded_live_csv_monitor_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage74 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE74_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\74_guarded_live_csv_monitor_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\75_external_action_payload_preview_audit_only"
for %%I in ("%STAGE74_DIR%") do set "STAGE74_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE74_DIR%\gold_v3_74_guarded_live_csv_monitor_summary.json" (
    echo [ERROR] Stage74 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE74_DIR%\gold_v3_74_latest_guarded_snapshot.json" (
    echo [ERROR] Stage74 latest guarded snapshot not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 75 EXTERNAL ACTION PAYLOAD PREVIEW AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE74_DIR=%STAGE74_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Preview only. No Discord send, no MT5 order, no AI API, no final signal.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_75_external_action_payload_preview_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage74-dir "%STAGE74_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 75 payload preview ended with errorlevel %ERR%.
    echo Paste this file if upload limit is reached:
    echo %OUTPUT_DIR%\gold_v3_75_PASTE_ME_EXTERNAL_ACTION_PAYLOAD_PREVIEW_SUMMARY.txt
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 75 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_75_PASTE_ME_EXTERNAL_ACTION_PAYLOAD_PREVIEW_SUMMARY.txt
echo.
pause
exit /b 0
