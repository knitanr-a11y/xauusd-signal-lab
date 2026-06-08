@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C63] GOLD V2 A002 fixed scope intake audit-only
echo [25C63] No condition change, replay, dry-run, source recovery, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c63_a002_fixed_scope_intake_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C63] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C63] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C63] Completed audit-only fixed scope intake output creation.
echo [25C63] Review FX_OUTPUTS\gold_v2_25c63_a002_fixed_scope_intake_audit_only before any next work.
echo.
pause
exit /b 0
