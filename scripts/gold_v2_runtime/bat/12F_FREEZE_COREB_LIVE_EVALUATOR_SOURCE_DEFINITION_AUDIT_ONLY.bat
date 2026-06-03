@echo off
setlocal

REM GOLD V2 12F - Freeze CoreB live evaluator source definition audit only.
REM This BAT creates a frozen CoreB source definition JSON for later mapping.
REM It does not write live mappings, connect step 13, send Discord notifications,
REM place MT5 orders, call AI API, or call live hooks.

cd /d "%~dp0\..\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

python scripts\gold_v2_runtime\freeze_gold_v2_coreb_live_evaluator_source_definition_audit_only.py %*
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] GOLD V2 12F CoreB source definition freeze audit failed.
  echo No Discord notification, MT5 order, AI API call, or live hook was performed.
  pause
  exit /b %EXIT_CODE%
)

echo.
echo [OK] GOLD V2 12F CoreB source definition freeze audit completed.
echo Review configs\gold_v2\frozen_coreB_live_evaluator_source_definition_20260603.json.
echo Review Files\FX_OUTPUTS\gold_v2_coreb_live_evaluator_source_definition_freeze_audit_only.
echo This is not a live mapping. Step 12 must be rerun/updated before any evaluator connection.
echo No Discord notification, MT5 order, AI API call, or live hook was performed.
pause
exit /b 0
