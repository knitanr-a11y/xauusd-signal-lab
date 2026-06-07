@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C48] GOLD V2 CoreB G1 representative filter set review spec audit-only
echo [25C48] This BAT writes a review specification only.
echo [25C48] No approval, replay, dry-run, source change, live path, AI API, Discord, MT5, or final signal is executed.
echo.

python scripts\gold_v2_runtime\audit_gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [25C48] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C48] STOP or error. Do not proceed.
  echo.
  pause
  exit /b %EXIT_CODE%
)

echo [25C48] Completed audit-only review spec output creation.
echo [25C48] Review FX_OUTPUTS\gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only before any next work.
echo.
pause
exit /b 0
