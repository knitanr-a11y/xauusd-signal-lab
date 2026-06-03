@echo off
setlocal

REM GOLD live-audit packet builder.
REM This bundles candidate JSON and notification preview into one audit packet.
REM No external transmission or order execution is performed.

cd /d "%~dp0\..\..\.."

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

python scripts\gold_v2_runtime\build_gold_v2_live_audit_packet_audit_only.py %*

if errorlevel 1 (
  echo.
  echo [ERROR] GOLD live-audit packet build failed.
  pause
  exit /b 1
)

echo.
echo [OK] GOLD live-audit packet build completed.
echo Output is under Files\FX_OUTPUTS\gold_v2_live_audit_packet_audit_only by default.
pause
endlocal
