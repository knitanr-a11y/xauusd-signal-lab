@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C50] GOLD V2 CoreB G1 representative dry-run readiness review audit-only
echo [25C50] This BAT reviews dry-run specification readiness only.
echo [25C50] No approval, replay, dry-run, source change, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c50_coreb_g1_representative_dry_run_readiness_review_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C50] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C50] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C50] Completed audit-only readiness review output creation.
echo [25C50] Review FX_OUTPUTS\gold_v2_25c50_coreb_g1_representative_dry_run_readiness_review_audit_only before any next work.
echo.
pause
exit /b 0
