@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_scalp_state_survival_shadow"
set "PY=%STATE%\venv\Scripts\python.exe"
set "CFG=%ROOT%\config\gold_scalp_state_survival_shadow\local_config.json"
if not exist "%PY%" (
  echo [BLOCKED] Run 01_INSTALL.bat first.
  pause
  exit /b 2
)
if not exist "%CFG%" (
  copy /Y "%ROOT%\config\gold_scalp_state_survival_shadow\local_config.example.json" "%CFG%" >nul
  echo Created %CFG%
  echo Confirm the V19 local config path, then run this BAT again.
  notepad "%CFG%"
  pause
  exit /b 2
)
pushd "%ROOT%"
"%PY%" -m scripts.gold_scalp_state_survival_shadow.shadow_runtime bootstrap --config "%CFG%"
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" goto :error
echo.
echo [OK] BOOTSTRAP PASS - no historical signal was backfilled.
pause
exit /b 0
:error
echo.
echo [BLOCKED] Command failed.
pause
exit /b 2
