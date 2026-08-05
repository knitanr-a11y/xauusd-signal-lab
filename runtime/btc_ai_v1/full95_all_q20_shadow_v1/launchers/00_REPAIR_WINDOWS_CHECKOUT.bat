@echo off
cd /d "%~dp0..\..\..\.."
python scripts\btc_ai_v1\repair_full95_shadow_windows_checkout.py
if errorlevel 1 (
  echo Repair failed. Do not run 02_INIT_ONCE.bat.
  pause
  exit /b 20
)
echo Repair completed. Run 02_INIT_ONCE.bat next.
pause
