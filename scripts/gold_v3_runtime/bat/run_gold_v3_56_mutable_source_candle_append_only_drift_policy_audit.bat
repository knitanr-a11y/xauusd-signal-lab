@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 56 mutable source candle append-only drift policy audit-only runner.
REM Classifies Stage55 strict checkpoint replay BLOCKED causes only.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\55_replay_from_checkpoint_dry_run_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\55_replay_from_checkpoint_dry_run_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\55_replay_from_checkpoint_dry_run_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\55_replay_from_checkpoint_dry_run_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage55 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE55_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\55_replay_from_checkpoint_dry_run_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\56_mutable_source_candle_append_only_drift_policy_audit_only"
for %%I in ("%STAGE55_DIR%") do set "STAGE55_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE55_DIR%\gold_v3_55_replay_dry_run_summary.json" (
    echo [ERROR] Stage55 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE55_DIR%\gold_v3_55_hash_recheck.csv" (
    echo [ERROR] Stage55 hash recheck not found.
    pause
    exit /b 1
)
if not exist "%STAGE55_DIR%\gold_v3_55_hash_mismatch_details.csv" (
    echo [ERROR] Stage55 hash mismatch details not found. Re-run patched Stage55 first.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 56 MUTABLE SOURCE DRIFT POLICY AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE55_DIR=%STAGE55_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo This classifies drift only. It does not mark Stage55 strict replay READY and does not enable live.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_56_mutable_source_candle_append_only_drift_policy_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage55-dir "%STAGE55_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 56 drift policy audit failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 56 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_56_PASTE_ME_DRIFT_POLICY_SUMMARY.txt
echo.
pause
exit /b 0
