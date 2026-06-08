@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C64] GOLD V2 A002 fixed scope package audit-only
echo [25C64] No condition change, replay, dry-run, source recovery, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c64_a002_fixed_scope_package_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C64] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C64] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C64] Completed audit-only fixed scope package output creation.
echo [25C64] Review FX_OUTPUTS\gold_v2_25c64_a002_fixed_scope_package_audit_only before any next work.
echo.
pause
exit /b 0
