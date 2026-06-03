@echo off
setlocal

REM GOLD V2 12H - Consolidate live evaluator mapping status audit only.
REM Read-only audit. Does not modify mappings, connect step 13, send Discord,
REM place MT5 orders, call AI API, or call live hooks.

cd /d "%~dp0\..\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

python scripts\gold_v2_runtime\consolidate_gold_v2_live_evaluator_mapping_status_audit_only.py %*
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] GOLD V2 12H consolidated mapping status audit failed.
  echo No Discord notification, MT5 order, AI API call, or live hook was performed.
  pause
  exit /b %EXIT_CODE%
)

echo.
echo [OK] GOLD V2 12H consolidated mapping status audit completed.
echo Review Files\FX_OUTPUTS\gold_v2_live_evaluator_mapping_consolidated_status_audit_only.
echo Read-only audit. Step 13 remains blocked.
echo No Discord notification, MT5 order, AI API call, or live hook was performed.
pause
exit /b 0
