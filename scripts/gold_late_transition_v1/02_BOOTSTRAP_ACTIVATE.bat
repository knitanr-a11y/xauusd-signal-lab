@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "CONFIG_DIR=%ROOT%\config\gold_late_transition_v1"
set "CONFIG=%CONFIG_DIR%\local_config.json"
set "EXAMPLE=%CONFIG_DIR%\local_config.example.json"
set "PY=%LOCALAPPDATA%\xauusd_signal_lab\gold_late_transition_v1_shadow\venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [BLOCKED] Run 01_INSTALL.bat first.
  exit /b 2
)
if not exist "%ROOT%\config\gold_wave_shadow_v19\local_config.json" (
  echo [BLOCKED] V19 local_config.json was not found. Keep the existing V19 setup unchanged.
  exit /b 2
)
if not exist "%CONFIG%" (
  copy "%EXAMPLE%" "%CONFIG%" >nul
  echo [INFO] Created Challenger local_config.json. It references the existing V19 local config.
)
pushd "%ROOT%"
"%PY%" -m scripts.gold_late_transition_v1.shadow_runtime --config "%CONFIG%" bootstrap --activate
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" exit /b %RC%
echo [OK] No-backfill Late Transition V1 prospective shadow activated.
endlocal
