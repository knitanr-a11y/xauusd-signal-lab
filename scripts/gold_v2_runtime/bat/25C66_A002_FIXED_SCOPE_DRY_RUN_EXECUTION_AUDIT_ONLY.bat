@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C66] GOLD V2 A002 fixed scope dry-run execution audit-only
echo [25C66] Creates audit-only ledger only. No live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c66_a002_fixed_scope_dry_run_execution_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C66] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C66] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C66] Completed audit-only fixed scope dry-run ledger creation.
echo [25C66] Review FX_OUTPUTS\gold_v2_25c66_a002_fixed_scope_dry_run_execution_audit_only before any next work.
echo.
pause
exit /b 0
