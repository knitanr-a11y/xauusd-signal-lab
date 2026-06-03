@echo off
setlocal

REM GOLD V2 step 12: map frozen rule-source manifests to live evaluator mappings.
REM Audit-only. No Discord notification, MT5 order, AI API, or live hook is performed.
REM NO_SIGNAL notification remains prohibited.
REM Exit code 2 means the audit gate intentionally stopped on UNMAPPED_CONDITION.

cd /d "%~dp0\..\..\.."

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

python scripts\gold_v2_runtime\map_gold_v2_frozen_rules_to_live_evaluator_audit_only.py %*
set "EXITCODE=%ERRORLEVEL%"

if "%EXITCODE%"=="2" (
  echo.
  echo [STOPPED] GOLD V2 frozen rule to live evaluator mapping found blocking UNMAPPED_CONDITION.
  echo Review Files\FX_OUTPUTS\gold_v2_live_evaluator_mapping_audit_only.
  echo No Discord notification, MT5 order, AI API call, or live hook was performed.
  pause
  exit /b 2
)

if not "%EXITCODE%"=="0" (
  echo.
  echo [ERROR] GOLD V2 frozen rule to live evaluator mapping audit failed.
  echo No Discord notification, MT5 order, AI API call, or live hook was performed.
  pause
  exit /b %EXITCODE%
)

echo.
echo [OK] GOLD V2 frozen rule to live evaluator mapping audit completed.
echo Output is under configs\gold_v2 and Files\FX_OUTPUTS\gold_v2_live_evaluator_mapping_audit_only by default.
echo No Discord notification, MT5 order, AI API call, or live hook was performed.
pause
endlocal
