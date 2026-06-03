@echo off
setlocal

REM GOLD V2 latest M15 feature snapshot and MEDIUM feature probe.
REM This is audit-only and feature-probe-only.
REM No external transmission or order execution is performed.

cd /d "%~dp0\..\..\.."

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

python scripts\gold_v2_runtime\build_gold_v2_latest_feature_snapshot_audit_only.py %*

if errorlevel 1 (
  echo.
  echo [ERROR] GOLD V2 latest feature snapshot audit probe failed.
  pause
  exit /b 1
)

echo.
echo [OK] GOLD V2 latest feature snapshot audit probe completed.
echo Output is under Files\FX_OUTPUTS\gold_v2_latest_feature_snapshot_audit_only by default.
pause
endlocal
