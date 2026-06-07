@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C52] GOLD V2 CoreB G1 dry-run source candidate review audit-only
echo [25C52] This BAT reviews/binds the top source candidate for future audit planning only.
echo [25C52] No source execution confirmation, approval, replay, dry-run, source change, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C52] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C52] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C52] Completed audit-only source candidate review output creation.
echo [25C52] Review FX_OUTPUTS\gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only before any next work.
echo.
pause
exit /b 0
