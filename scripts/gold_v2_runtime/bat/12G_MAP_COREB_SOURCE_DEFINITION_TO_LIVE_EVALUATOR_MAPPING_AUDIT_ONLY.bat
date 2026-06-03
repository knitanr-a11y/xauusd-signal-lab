@echo off
setlocal

REM GOLD V2 12G - Map frozen CoreB source definition to audit-only live evaluator mapping.
REM This BAT updates CoreB mapping only in final-signal-blocked audit state.
REM It does not connect step 13, send Discord notifications, place MT5 orders,
REM call AI API, or call live hooks.

cd /d "%~dp0\..\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

python scripts\gold_v2_runtime\map_gold_v2_coreb_source_definition_to_live_evaluator_mapping_audit_only.py %*
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] GOLD V2 12G CoreB source-definition-to-mapping audit failed.
  echo No Discord notification, MT5 order, AI API call, or live hook was performed.
  pause
  exit /b %EXIT_CODE%
)

echo.
echo [OK] GOLD V2 12G CoreB audit mapping completed.
echo Review configs\gold_v2\live_evaluator_mapping_coreB_20260603.json.
echo Review Files\FX_OUTPUTS\gold_v2_coreb_live_evaluator_mapping_from_source_definition_audit_only.
echo CoreB is audit mapping-ready only. Step 13 remains blocked.
echo No Discord notification, MT5 order, AI API call, or live hook was performed.
pause
exit /b 0
