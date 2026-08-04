@echo off
setlocal
title GOLD P75 State Survival Shadow - Observation Loop
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_scalp_state_survival_shadow"
set "PY=%STATE%\venv\Scripts\python.exe"
set "CFG=%ROOT%\config\gold_scalp_state_survival_shadow\local_config.json"
echo ============================================================
echo GOLD P75 STATE SURVIVAL SHADOW - OBSERVATION LOOP
echo Candidate: CANDLE_STATE_SURVIVAL_DUAL_STRICT_EPISODE_HEALTH_P75_V3
echo Observation only / MT5 orders OFF
echo Close this window to stop only the P75 State Survival loop.
echo ============================================================
if not exist "%PY%" (
  echo [GOLD_P75_STATE_SURVIVAL_SHADOW] [BLOCKED] Run 01_INSTALL.bat first.
  pause
  exit /b 2
)
if not exist "%CFG%" (
  echo [GOLD_P75_STATE_SURVIVAL_SHADOW] [BLOCKED] Run 02_BOOTSTRAP_ACTIVATE_SHADOW.bat first.
  pause
  exit /b 2
)
pushd "%ROOT%"
"%PY%" -m scripts.gold_scalp_state_survival_shadow.shadow_runtime run-loop --config "%CFG%"
set "RC=%ERRORLEVEL%"
popd
echo.
echo [GOLD_P75_STATE_SURVIVAL_SHADOW] Loop stopped. MT5 orders were never enabled.
pause
exit /b %RC%
