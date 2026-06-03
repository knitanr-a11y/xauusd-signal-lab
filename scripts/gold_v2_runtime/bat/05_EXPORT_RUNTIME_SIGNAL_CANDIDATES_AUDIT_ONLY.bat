@echo off
setlocal

REM GOLD V2 runtime signal candidate exporter.
REM This reads the audit ledger from 03_RUN_COREA_COREB_MEDIUM_AUDIT_ONLY.bat
REM and outputs runtime-shaped CSV/JSONL candidates.
REM No AI, Discord, MT5, or live trading APIs are called.

cd /d "%~dp0\..\..\.."

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

python scripts\gold_v2_runtime\export_gold_v2_runtime_signal_candidates_audit_only.py %*

if errorlevel 1 (
  echo.
  echo [ERROR] GOLD V2 runtime signal candidate export failed.
  pause
  exit /b 1
)

echo.
echo [OK] GOLD V2 runtime signal candidate export completed.
echo Output is under Files\FX_OUTPUTS\gold_v2_runtime_signal_candidates_audit_only by default.
pause
endlocal
