@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C54] GOLD V2 CoreB G1 dry-run execution gate review audit-only
echo [25C54] This BAT reviews the dry-run execution gate only and keeps it closed.
echo [25C54] No source execution confirmation, approval, replay, dry-run, source change, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c54_coreb_g1_dry_run_execution_gate_review_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C54] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C54] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C54] Completed audit-only dry-run execution gate review output creation.
echo [25C54] Review FX_OUTPUTS\gold_v2_25c54_coreb_g1_dry_run_execution_gate_review_audit_only before any next work.
echo.
pause
exit /b 0
