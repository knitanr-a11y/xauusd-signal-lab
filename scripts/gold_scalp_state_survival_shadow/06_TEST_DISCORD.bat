@echo off
setlocal
title GOLD P75 State Survival Shadow - Discord Test
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_scalp_state_survival_shadow"
set "PY=%STATE%\venv\Scripts\python.exe"
set "CFG=%ROOT%\config\gold_scalp_state_survival_shadow\local_config.json"
echo ============================================================
echo GOLD P75 STATE SURVIVAL SHADOW - DISCORD TEST
echo Entry notification only / MT5 orders OFF
echo ============================================================
if not exist "%PY%" (
  echo [GOLD_P75_STATE_SURVIVAL_SHADOW] [BLOCKED] Run 01_INSTALL.bat first.
  pause
  exit /b 2
)
if not exist "%CFG%" (
  copy /Y "%ROOT%\config\gold_scalp_state_survival_shadow\local_config.example.json" "%CFG%" >nul
  echo [GOLD_P75_STATE_SURVIVAL_SHADOW] Created %CFG%
  echo Confirm the V19 local config path, then run this BAT again.
  notepad "%CFG%"
  pause
  exit /b 2
)
pushd "%ROOT%"
"%PY%" -m scripts.gold_scalp_state_survival_shadow.shadow_runtime test-discord --config "%CFG%"
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" goto :error
echo.
echo [GOLD_P75_STATE_SURVIVAL_SHADOW] [OK] DISCORD TEST PASS
pause
exit /b 0
:error
echo.
echo [GOLD_P75_STATE_SURVIVAL_SHADOW] [BLOCKED] Command failed.
pause
exit /b 2
