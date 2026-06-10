@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 59 mutable source prefix-hash support audit-only runner.
REM Creates first prefix-hash baseline for mutable source candles.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\58_bounded_checkpoint_replay_dry_run_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\58_bounded_checkpoint_replay_dry_run_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\58_bounded_checkpoint_replay_dry_run_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\58_bounded_checkpoint_replay_dry_run_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage58 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE57_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\57_bounded_replay_window_freeze_decision_audit_only"
set "STAGE58_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\58_bounded_checkpoint_replay_dry_run_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\59_mutable_source_prefix_hash_support_audit_only"
for %%I in ("%STAGE57_DIR%") do set "STAGE57_DIR=%%~fI"
for %%I in ("%STAGE58_DIR%") do set "STAGE58_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE57_DIR%\gold_v3_57_bounded_replay_summary.json" (
    echo [ERROR] Stage57 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE57_DIR%\gold_v3_57_mutable_source_window_freeze.csv" (
    echo [ERROR] Stage57 mutable source window freeze not found.
    pause
    exit /b 1
)
if not exist "%STAGE58_DIR%\gold_v3_58_bounded_replay_summary.json" (
    echo [ERROR] Stage58 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE58_DIR%\gold_v3_58_mutable_source_bounded_window.csv" (
    echo [ERROR] Stage58 mutable source bounded window not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 59 MUTABLE SOURCE PREFIX HASH SUPPORT AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo This creates the first prefix-hash baseline only. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_59_mutable_source_prefix_hash_support_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage57-dir "%STAGE57_DIR%" ^
  --stage58-dir "%STAGE58_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 59 prefix hash support audit failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 59 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_59_PASTE_ME_PREFIX_HASH_SUMMARY.txt
echo.
pause
exit /b 0
