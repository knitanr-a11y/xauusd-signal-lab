@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C62] GOLD V2 CoreB G1 A002 fixed dry-run direction package audit-only
echo [25C62] This BAT consolidates fixed-condition dry-run gates into one human-direction package.
echo [25C62] No condition change, approval, replay, dry-run, source recovery, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c62_coreb_g1_a002_fixed_dry_run_direction_package_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C62] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C62] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C62] Completed audit-only fixed dry-run direction package output creation.
echo [25C62] Review FX_OUTPUTS\gold_v2_25c62_coreb_g1_a002_fixed_dry_run_direction_package_audit_only before any next work.
echo.
pause
exit /b 0
