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
  echo [BLOCKED] Run 02_BOOTSTRAP_ACTIVATE_SHADOW.bat first.
  pause
  exit /b 2
)
pushd "%ROOT%"
"%PY%" -m scripts.gold_scalp_state_survival_shadow.shadow_runtime run-loop --config "%CFG%"
set "RC=%ERRORLEVEL%"
popd
echo.
echo Shadow loop stopped. MT5 orders were never enabled.
pause
exit /b %RC%
