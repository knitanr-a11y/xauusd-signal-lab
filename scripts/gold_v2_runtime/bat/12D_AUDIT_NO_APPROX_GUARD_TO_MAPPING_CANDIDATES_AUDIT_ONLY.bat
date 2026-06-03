@echo off
setlocal

REM GOLD V2 12D - NO_APPROX_GUARD to mapping candidates audit only.
REM Candidate rows are not live rules.
REM This BAT does not send Discord notifications, place MT5 orders, call AI API, or call live hooks.
REM Step 13 remains blocked until step 12 has no blocking UNMAPPED_CONDITION.

cd /d "%~dp0\..\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

python scripts\gold_v2_runtime\audit_gold_v2_no_approx_guard_to_mapping_candidates_audit_only.py %*
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] GOLD V2 12D no-approx guard mapping candidate audit failed.
  echo No Discord notification, MT5 order, AI API call, or live hook was performed.
  pause
  exit /b %EXIT_CODE%
)

echo.
echo [OK] GOLD V2 12D no-approx guard mapping candidate audit completed.
echo Review Files\FX_OUTPUTS\gold_v2_no_approx_guard_mapping_candidates_audit_only.
echo Candidate rows are not live rules. Step 13 remains blocked until step 12 has no blocking UNMAPPED_CONDITION.
echo No Discord notification, MT5 order, AI API call, or live hook was performed.
pause
exit /b 0
