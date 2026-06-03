@echo off
setlocal

REM GOLD V2 12C - candidate rule-definition inventory audit only.
REM Candidate evidence is not a live rule.
REM This BAT does not send Discord notifications, place MT5 orders, call AI API, or call live hooks.
REM Step 13 remains blocked until step 12 has no blocking UNMAPPED_CONDITION.

cd /d "%~dp0\..\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

python scripts\gold_v2_runtime\audit_gold_v2_candidate_rule_definition_inventory_audit_only.py %*
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] GOLD V2 12C candidate rule-definition inventory audit failed.
  echo No Discord notification, MT5 order, AI API call, or live hook was performed.
  pause
  exit /b %EXIT_CODE%
)

echo.
echo [OK] GOLD V2 12C candidate rule-definition inventory audit completed.
echo Review Files\FX_OUTPUTS\gold_v2_candidate_rule_definition_inventory_audit_only.
echo Candidate evidence is not a live rule. Step 13 remains blocked until step 12 has no blocking UNMAPPED_CONDITION.
echo No Discord notification, MT5 order, AI API call, or live hook was performed.
pause
exit /b 0
