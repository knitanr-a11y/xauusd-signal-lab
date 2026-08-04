@echo off
setlocal
title GOLD Challenger C1 Shadow - Discord Entry Alerts
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow"
set "CONFIG=%STATE%\local_config.json"
set "PY=%STATE%\venv\Scripts\python.exe"
echo ============================================================
echo GOLD CHALLENGER C1 SHADOW - DISCORD ENTRY ALERT LOOP
echo Accepted Challenger entries only / Observation only
echo MT5 orders OFF / V19 notifications are separate
echo Close this window to stop only Challenger C1 Discord alerts.
echo ============================================================
if not exist "%PY%" (
  echo [GOLD_CHALLENGER_C1_SHADOW] [BLOCKED] Run 01_INSTALL_SHADOW.bat first.
  pause
  exit /b 2
)
if not exist "%CONFIG%" (
  echo [GOLD_CHALLENGER_C1_SHADOW] [BLOCKED] local_config.json is missing:
  echo %CONFIG%
  pause
  exit /b 2
)
pushd "%ROOT%"
"%PY%" -m scripts.gold_challenger_c1.discord_notifier --config "%CONFIG%" loop
set "RC=%ERRORLEVEL%"
popd
echo.
echo [GOLD_CHALLENGER_C1_SHADOW] Discord alert loop stopped.
pause
exit /b %RC%
