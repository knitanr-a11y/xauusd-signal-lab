@echo off
setlocal
title GOLD Challenger C1 Shadow - Bootstrap Activate
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow"
set "CONFIG=%STATE%\local_config.json"
set "EXAMPLE=%ROOT%\config\gold_challenger_c1\local_shadow_config.example.json"
set "PY=%STATE%\venv\Scripts\python.exe"
echo ============================================================
echo GOLD CHALLENGER C1 SHADOW - BOOTSTRAP / ACTIVATE
echo No backfill / V19 read-only priority / MT5 orders OFF
echo ============================================================
if not exist "%PY%" (
  echo [GOLD_CHALLENGER_C1_SHADOW] [BLOCKED] Run 01_INSTALL_SHADOW.bat first.
  pause
  exit /b 2
)
if not exist "%CONFIG%" (
  copy "%EXAMPLE%" "%CONFIG%" >nul
  echo [GOLD_CHALLENGER_C1_SHADOW] [ACTION REQUIRED] local_config.json was created outside the repository:
  echo %CONFIG%
  echo Confirm the V19 local_config path and data source inheritance, save, then run this BAT again.
  start "" notepad "%CONFIG%"
  pause
  exit /b 2
)
pushd "%ROOT%"
"%PY%" -m scripts.gold_challenger_c1.shadow_runtime --config "%CONFIG%" bootstrap --activate
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" (
  echo [GOLD_CHALLENGER_C1_SHADOW] [BLOCKED] Bootstrap failed. V19 was not modified.
  pause
  exit /b %RC%
)
echo [GOLD_CHALLENGER_C1_SHADOW] [OK] No-backfill Shadow activated or existing activation preserved.
pause
