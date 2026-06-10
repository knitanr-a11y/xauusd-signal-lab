@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 61 frozen audit package human review audit-only runner.
REM Builds review package only. No live enablement.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\60_mutable_source_prefix_hash_verification_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\60_mutable_source_prefix_hash_verification_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\60_mutable_source_prefix_hash_verification_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\60_mutable_source_prefix_hash_verification_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage60 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\61_frozen_audit_package_human_review_audit_only"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%CANDLE_DIR%\FX_OUTPUTS\gold_v3\60_mutable_source_prefix_hash_verification_audit_only\gold_v3_60_prefix_hash_verification_summary.json" (
    echo [ERROR] Stage60 summary not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 61 FROZEN AUDIT PACKAGE HUMAN REVIEW AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Builds review package only. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_61_frozen_audit_package_human_review_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 61 frozen audit package failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 61 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_61_PASTE_ME_FROZEN_AUDIT_PACKAGE_SUMMARY.txt
echo.
pause
exit /b 0
