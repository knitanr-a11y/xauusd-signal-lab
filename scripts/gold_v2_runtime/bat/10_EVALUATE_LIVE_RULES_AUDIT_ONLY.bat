@echo off
setlocal

REM GOLD V2 live rule evaluation audit gate.
REM No Discord notification, MT5 order, AI API, or live hook is performed.
REM NO_SIGNAL intentionally produces an empty notification preview.

cd /d "%~dp0\..\..\.."

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

python scripts\gold_v2_runtime\evaluate_gold_v2_live_rules_audit_only.py %*

if errorlevel 1 (
  echo.
  echo [ERROR] GOLD V2 live rule evaluation audit gate failed.
  pause
  exit /b 1
)

echo.
echo [OK] GOLD V2 live rule evaluation audit gate completed.
echo Output is under Files\FX_OUTPUTS\gold_v2_live_rule_evaluation_audit_only by default.
pause
endlocal
