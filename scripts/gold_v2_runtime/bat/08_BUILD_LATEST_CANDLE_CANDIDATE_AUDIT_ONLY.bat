@echo off
setlocal

REM GOLD latest-candle candidate audit bridge.
REM Filters audited runtime candidates by latest M15 candle timestamp or --eval-time.
REM No external transmission or order execution is performed.

cd /d "%~dp0\..\..\.."

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

python scripts\gold_v2_runtime\build_gold_v2_latest_candle_candidate_audit_only.py %*

if errorlevel 1 (
  echo.
  echo [ERROR] GOLD latest-candle candidate audit bridge failed.
  pause
  exit /b 1
)

echo.
echo [OK] GOLD latest-candle candidate audit bridge completed.
echo Output is under Files\FX_OUTPUTS\gold_v2_latest_candle_candidate_audit_only by default.
pause
endlocal
