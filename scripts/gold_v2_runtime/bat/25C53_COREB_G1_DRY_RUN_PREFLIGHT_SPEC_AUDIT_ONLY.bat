@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C53] GOLD V2 CoreB G1 dry-run preflight spec audit-only
echo [25C53] This BAT writes a future dry-run preflight specification package only.
echo [25C53] No source execution confirmation, approval, replay, dry-run, source change, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C53] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C53] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C53] Completed audit-only dry-run preflight spec output creation.
echo [25C53] Review FX_OUTPUTS\gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only before any next work.
echo.
pause
exit /b 0
