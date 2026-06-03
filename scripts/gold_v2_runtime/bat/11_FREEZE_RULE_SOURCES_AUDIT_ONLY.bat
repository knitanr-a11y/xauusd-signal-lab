@echo off
setlocal

REM GOLD V2 frozen rule source generator.
REM Creates local configs/gold_v2/frozen_*.json manifests from audited exploration outputs.
REM No Discord notification, MT5 order, AI API, or live hook is performed.

cd /d "%~dp0\..\..\.."

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

python scripts\gold_v2_runtime\freeze_gold_v2_rule_sources_audit_only.py %*

if errorlevel 1 (
  echo.
  echo [ERROR] GOLD V2 frozen rule source generation failed.
  pause
  exit /b 1
)

echo.
echo [OK] GOLD V2 frozen rule source generation completed.
echo Configs are written under configs\gold_v2 and audit copies under Files\FX_OUTPUTS\gold_v2_frozen_rule_sources_audit_only.
pause
endlocal
