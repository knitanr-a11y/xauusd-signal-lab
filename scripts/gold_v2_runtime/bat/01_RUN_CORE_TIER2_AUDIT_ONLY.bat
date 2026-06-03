@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
for %%I in ("%REPO_ROOT%\..\..") do set "FILES_DIR=%%~fI"

set "SCRIPT=%REPO_ROOT%\scripts\gold_v2_runtime\evaluate_gold_v2_core_tier2_audit_only.py"
set "INPUT_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v2_ABC_stack_cap_2025_2026_validation_outputs"
set "OUTPUT_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v2_core_tier2_audit_only"

echo [GOLD V2] Core/Tier2 audit-only evaluator
echo REPO_ROOT=%REPO_ROOT%
echo INPUT_DIR=%INPUT_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.

if not exist "%SCRIPT%" (
  echo [ERROR] Script not found: %SCRIPT%
  pause
  exit /b 1
)

if not exist "%INPUT_DIR%\abc_stack_cap_2025_fold4_cluster_ledger.csv" (
  echo [ERROR] Missing input: %INPUT_DIR%\abc_stack_cap_2025_fold4_cluster_ledger.csv
  echo Please copy or generate gold_v2_ABC_stack_cap_2025_2026_validation_outputs under Files\FX_OUTPUTS first.
  pause
  exit /b 2
)

if not exist "%INPUT_DIR%\abc_stack_cap_2026_cluster_ledger.csv" (
  echo [ERROR] Missing input: %INPUT_DIR%\abc_stack_cap_2026_cluster_ledger.csv
  echo Please copy or generate gold_v2_ABC_stack_cap_2025_2026_validation_outputs under Files\FX_OUTPUTS first.
  pause
  exit /b 2
)

python "%SCRIPT%" ^
  --input-dir "%INPUT_DIR%" ^
  --output-dir "%OUTPUT_DIR%" ^
  --tier2-trend-eff96-max 0.4 ^
  --tier2-ret96-max -25 ^
  --strict

set "RC=%ERRORLEVEL%"
echo.
echo [GOLD V2] Finished with exit code %RC%
echo Output dir: %OUTPUT_DIR%
pause
exit /b %RC%
