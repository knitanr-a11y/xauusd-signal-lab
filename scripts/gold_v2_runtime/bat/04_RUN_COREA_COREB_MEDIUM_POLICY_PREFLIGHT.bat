@echo off
setlocal

REM GOLD V2 CoreA/CoreB/MEDIUM policy preflight.
REM This validates config and required audit input files only.
REM No AI, Discord, MT5, or live trading APIs are called.

cd /d "%~dp0\..\..\.."

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

python scripts\gold_v2_runtime\preflight_gold_v2_coreA_coreB_medium_policy.py %*

if errorlevel 1 (
  echo.
  echo [ERROR] GOLD V2 policy preflight failed.
  pause
  exit /b 1
)

echo.
echo [OK] GOLD V2 policy preflight completed.
echo Output is under Files\FX_OUTPUTS\gold_v2_coreA_coreB_medium_policy_preflight by default.
pause
endlocal
