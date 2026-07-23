@echo off
setlocal
set "ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"
set "INPUT=%ROOT%\outputs\M8A\frozen_inputs\LATEST"
set "OUTPUT=%ROOT%\outputs\M8A"
set "SCRIPT=%~dp0..\python\run_coverage_audit.py"

python "%SCRIPT%" --input-dir "%INPUT%" --output-root "%OUTPUT%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M8A coverage audit blocked. Keep audit-only; do not enable Discord/MT5/live/final signal.
  pause
  exit /b %RC%
)
echo [OK] 02 complete. Run 03_open_latest_results.bat to open the result folder.
pause
exit /b 0
