@echo off
setlocal
title GOLD Challenger C1 Shadow - Run Once Recovery Only
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow"
set "CONFIG=%STATE%\local_config.json"
set "PY=%STATE%\venv\Scripts\python.exe"
echo ============================================================
echo GOLD CHALLENGER C1 SHADOW - RUN ONCE / RECOVERY ONLY
echo No new entry backfill / V19 read-only / MT5 orders OFF
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
"%PY%" -m scripts.gold_challenger_c1.shadow_runtime --config "%CONFIG%" once
set "RC=%ERRORLEVEL%"
popd
pause
exit /b %RC%
