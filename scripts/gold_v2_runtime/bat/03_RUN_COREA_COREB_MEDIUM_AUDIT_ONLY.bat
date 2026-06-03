@echo off
setlocal

REM GOLD V2 CoreA + CoreB RR125 + MEDIUM audit-only runner.
REM This does not call AI, Discord, MT5, or live trading APIs.

cd /d "%~dp0\..\..\.."

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

python scripts\gold_v2_runtime\evaluate_gold_v2_coreA_coreB_medium_audit_only.py %*

if errorlevel 1 (
  echo.
  echo [ERROR] CoreA/CoreB/MEDIUM audit failed.
  pause
  exit /b 1
)

echo.
echo [OK] CoreA/CoreB/MEDIUM audit completed.
echo Output is under Files\FX_OUTPUTS\gold_v2_coreA_coreB_medium_audit_only by default.
pause
endlocal
