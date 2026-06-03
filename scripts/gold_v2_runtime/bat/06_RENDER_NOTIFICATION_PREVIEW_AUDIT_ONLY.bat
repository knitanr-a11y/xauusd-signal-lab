@echo off
setlocal

REM GOLD V2 notification preview renderer.
REM This renders message text only. No external transmission is performed.

cd /d "%~dp0\..\..\.."

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

python scripts\gold_v2_runtime\render_gold_v2_notification_preview_audit_only.py %*

if errorlevel 1 (
  echo.
  echo [ERROR] GOLD V2 notification preview render failed.
  pause
  exit /b 1
)

echo.
echo [OK] GOLD V2 notification preview render completed.
echo Output is under Files\FX_OUTPUTS\gold_v2_notification_preview_audit_only by default.
pause
endlocal
