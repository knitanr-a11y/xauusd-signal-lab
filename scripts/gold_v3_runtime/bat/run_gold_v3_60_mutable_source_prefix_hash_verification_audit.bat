@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 60 mutable source prefix-hash verification audit-only runner.
REM Verifies Stage59 prefix-hash baseline. No live enablement.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\59_mutable_source_prefix_hash_support_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\59_mutable_source_prefix_hash_support_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\59_mutable_source_prefix_hash_support_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\59_mutable_source_prefix_hash_support_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage59 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE59_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\59_mutable_source_prefix_hash_support_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\60_mutable_source_prefix_hash_verification_audit_only"
for %%I in ("%STAGE59_DIR%") do set "STAGE59_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE59_DIR%\gold_v3_59_prefix_hash_summary.json" (
    echo [ERROR] Stage59 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE59_DIR%\gold_v3_59_mutable_source_prefix_hash_snapshot.csv" (
    echo [ERROR] Stage59 prefix hash snapshot not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 60 MUTABLE SOURCE PREFIX HASH VERIFICATION AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE59_DIR=%STAGE59_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Verifies Stage59 prefix-hash baseline. Appended rows are allowed. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_60_mutable_source_prefix_hash_verification_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage59-dir "%STAGE59_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 60 prefix hash verification failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 60 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_60_PASTE_ME_PREFIX_HASH_VERIFY_SUMMARY.txt
echo.
pause
exit /b 0
