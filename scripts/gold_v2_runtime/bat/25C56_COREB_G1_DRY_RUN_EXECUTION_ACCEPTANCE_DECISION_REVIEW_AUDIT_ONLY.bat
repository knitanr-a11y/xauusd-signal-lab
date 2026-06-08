@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C56] GOLD V2 CoreB G1 dry-run acceptance decision review audit-only
echo [25C56] This BAT reviews whether any decision marker is present.
echo [25C56] No acceptance, gate open, approval, replay, dry-run, source change, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c56_coreb_g1_dry_run_execution_acceptance_decision_review_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C56] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C56] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C56] Completed audit-only decision review output creation.
echo [25C56] Review FX_OUTPUTS\gold_v2_25c56_coreb_g1_dry_run_execution_acceptance_decision_review_audit_only before any next work.
echo.
pause
exit /b 0
