@echo off
setlocal

REM GOLD V2 12B - audit unresolved CoreA/CoreB live evaluator source definitions only.
REM This BAT does not send Discord notifications, place MT5 orders, call AI API, or call live hooks.
REM Candidate evidence is not a live rule. Step 13 remains blocked until step 12 has no blocking UNMAPPED_CONDITION.

cd /d "%~dp0\..\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

python scripts\gold_v2_runtime\audit_gold_v2_unmapped_rule_source_definitions_audit_only.py %*
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] GOLD V2 12B unmapped rule source definition audit failed.
  echo No Discord notification, MT5 order, AI API call, or live hook was performed.
  pause
  exit /b %EXIT_CODE%
)

echo.
echo [OK] GOLD V2 12B unmapped rule source definition audit completed.
echo Review Files\FX_OUTPUTS\gold_v2_unmapped_rule_source_definition_audit_only.
echo Candidate evidence is not a live rule. Step 13 remains blocked until step 12 has no blocking UNMAPPED_CONDITION.
echo No Discord notification, MT5 order, AI API call, or live hook was performed.
pause
exit /b 0
