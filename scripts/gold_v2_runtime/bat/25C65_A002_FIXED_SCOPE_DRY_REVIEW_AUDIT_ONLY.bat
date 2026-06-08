@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C65] GOLD V2 A002 fixed scope dry review audit-only
echo [25C65] Selects fixed A002 rows for audit review only.
echo [25C65] No condition change, replay, dry-run action, source recovery, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c65_a002_fixed_scope_dry_review_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C65] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C65] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C65] Completed audit-only fixed scope dry review output creation.
echo [25C65] Review FX_OUTPUTS\gold_v2_25c65_a002_fixed_scope_dry_review_audit_only before any next work.
echo.
pause
exit /b 0
