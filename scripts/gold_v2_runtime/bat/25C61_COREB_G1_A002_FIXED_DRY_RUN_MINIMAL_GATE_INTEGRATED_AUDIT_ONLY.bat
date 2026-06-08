@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C61] GOLD V2 CoreB G1 A002 fixed dry-run minimal gate integrated audit-only
echo [25C61] This BAT keeps A002 and retained filters fixed and reviews minimal dry-run gates only.
echo [25C61] No condition change, approval, replay, dry-run, source recovery, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c61_coreb_g1_a002_fixed_dry_run_minimal_gate_integrated_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C61] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C61] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C61] Completed integrated audit-only minimal gate output creation.
echo [25C61] Review FX_OUTPUTS\gold_v2_25c61_coreb_g1_a002_fixed_dry_run_minimal_gate_integrated_audit_only before any next work.
echo.
pause
exit /b 0
