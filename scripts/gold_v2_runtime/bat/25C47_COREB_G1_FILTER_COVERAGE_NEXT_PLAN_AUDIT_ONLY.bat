@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C47] GOLD V2 CoreB G1 filter coverage next plan audit-only
echo [25C47] This BAT only reads 25C46 artifacts and writes a next-plan package.
echo [25C47] No replay, dry-run, source change, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C47] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C47] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C47] Completed audit-only next-plan output creation.
echo [25C47] Review FX_OUTPUTS\gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only before any next work.
echo.
pause
exit /b 0
