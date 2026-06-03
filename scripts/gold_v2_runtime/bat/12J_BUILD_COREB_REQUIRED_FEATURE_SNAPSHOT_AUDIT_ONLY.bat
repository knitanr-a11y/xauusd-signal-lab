@echo off
setlocal
cd /d "%~dp0\..\..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python scripts\gold_v2_runtime\build_gold_v2_coreb_required_feature_snapshot_audit_only.py %*
set EXIT_CODE=%ERRORLEVEL%
if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] GOLD V2 12J feature snapshot audit failed.
  pause
  exit /b %EXIT_CODE%
)
echo.
echo [OK] GOLD V2 12J feature snapshot audit completed.
echo Review Files\FX_OUTPUTS\gold_v2_coreb_required_feature_snapshot_audit_only.
echo Candidate feature snapshot only. Step 13 remains blocked.
pause
exit /b 0
