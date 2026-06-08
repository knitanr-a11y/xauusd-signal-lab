@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C60] GOLD V2 CoreB G1 dry-run blocked status final handoff audit-only
echo [25C60] This BAT writes final blocked-status handoff only.
echo [25C60] No acceptance, gate open, approval, replay, dry-run, source change, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c60_coreb_g1_dry_run_blocked_status_final_handoff_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C60] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C60] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C60] Completed audit-only final blocked-status handoff output creation.
echo [25C60] Review FX_OUTPUTS\gold_v2_25c60_coreb_g1_dry_run_blocked_status_final_handoff_audit_only before any next work.
echo.
pause
exit /b 0
