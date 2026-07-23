@echo off
setlocal
set "ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"
set "SOURCE=%ROOT%\logs\m7c"
set "FREEZE=%ROOT%\outputs\M8A\frozen_inputs"
set "SCRIPT=%~dp0..\python\prepare_inputs.py"

python "%SCRIPT%" --source-dir "%SOURCE%" --freeze-root "%FREEZE%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M8A input freeze failed. Do not rerun M7C initializer or reset the runtime manifest.
  pause
  exit /b %RC%
)
echo [OK] 01 complete. Next, run 02_run_coverage_audit.bat once.
pause
exit /b 0
