@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 77 release gate packet audit-only.
REM Verifies Stage76 output and keeps live release blocked pending explicit human approval.
REM No Discord send, no MT5 order, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\76_full_audit_monitor_with_payload_preview_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\76_full_audit_monitor_with_payload_preview_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\76_full_audit_monitor_with_payload_preview_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\76_full_audit_monitor_with_payload_preview_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage76 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE76_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\76_full_audit_monitor_with_payload_preview_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\77_release_gate_packet_audit_only"
for %%I in ("%STAGE76_DIR%") do set "STAGE76_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE76_DIR%\gold_v3_76_full_audit_monitor_with_payload_preview_summary.json" (
    echo [ERROR] Stage76 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE76_DIR%\gold_v3_76_latest_payload_preview.json" (
    echo [ERROR] Stage76 latest payload preview not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 77 RELEASE GATE PACKET AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE76_DIR=%STAGE76_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Audit-only release gate packet. Live release remains blocked pending explicit human approval.
echo No Discord send, no MT5 order, no AI API, no final signal.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_77_release_gate_packet_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage76-dir "%STAGE76_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 77 release gate packet ended with errorlevel %ERR%.
    echo Paste this file if upload limit is reached:
    echo %OUTPUT_DIR%\gold_v3_77_PASTE_ME_RELEASE_GATE_PACKET_SUMMARY.txt
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 77 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_77_PASTE_ME_RELEASE_GATE_PACKET_SUMMARY.txt
echo.
pause
exit /b 0
