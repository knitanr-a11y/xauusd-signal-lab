@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow"
set "CONFIG=%STATE%\local_config.json"
set "EXAMPLE=%ROOT%\config\gold_challenger_c1\local_shadow_config.example.json"
set "PY=%STATE%\venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [BLOCKED] Run 01_INSTALL_SHADOW.bat first.
  pause
  exit /b 2
)
if not exist "%CONFIG%" (
  copy "%EXAMPLE%" "%CONFIG%" >nul
  echo [ACTION REQUIRED] Challenger local_config.json was created outside the repository:
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
  echo [BLOCKED] Challenger bootstrap failed. V19 was not modified.
  pause
  exit /b %RC%
)
echo [OK] Challenger C1 no-backfill Shadow activated.
pause
