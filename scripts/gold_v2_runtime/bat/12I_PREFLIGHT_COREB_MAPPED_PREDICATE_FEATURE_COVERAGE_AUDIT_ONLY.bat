@echo off
setlocal
cd /d "%~dp0\..\..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python scripts\gold_v2_runtime\preflight_gold_v2_coreb_mapped_predicate_feature_coverage_audit_only.py %*
set EXIT_CODE=%ERRORLEVEL%
if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] GOLD V2 12I preflight failed.
  pause
  exit /b %EXIT_CODE%
)
echo.
echo [OK] GOLD V2 12I preflight completed.
echo Review Files\FX_OUTPUTS\gold_v2_coreb_mapped_predicate_feature_coverage_preflight_audit_only.
echo Header-only audit. Step 13 remains blocked.
pause
exit /b 0
