@echo off
setlocal

REM GOLD V2 12E - CoreB source rule universe freeze-readiness audit only.
REM This BAT does not write live mappings, connect step 13, send Discord notifications,
REM place MT5 orders, call AI API, or call live hooks.

cd /d "%~dp0\..\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

python scripts\gold_v2_runtime\audit_gold_v2_coreb_source_rule_universe_freeze_readiness_audit_only.py %*
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] GOLD V2 12E CoreB source rule universe freeze-readiness audit failed.
  echo No Discord notification, MT5 order, AI API call, or live hook was performed.
  pause
  exit /b %EXIT_CODE%
)

echo.
echo [OK] GOLD V2 12E CoreB source rule universe freeze-readiness audit completed.
echo Review Files\FX_OUTPUTS\gold_v2_coreb_source_rule_universe_freeze_readiness_audit_only.
echo This is not a live mapping. Step 13 remains blocked until step 12 has no blocking UNMAPPED_CONDITION.
echo No Discord notification, MT5 order, AI API call, or live hook was performed.
pause
exit /b 0
