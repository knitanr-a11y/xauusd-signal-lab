@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C51] GOLD V2 CoreB G1 dry-run source concretion review audit-only
echo [25C51] This BAT searches local FX_OUTPUTS candidate source artifacts by path/name scoring only.
echo [25C51] No source confirmation, approval, replay, dry-run, source change, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C51] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C51] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C51] Completed audit-only source concretion review output creation.
echo [25C51] Review FX_OUTPUTS\gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only before any next work.
echo.
pause
exit /b 0
