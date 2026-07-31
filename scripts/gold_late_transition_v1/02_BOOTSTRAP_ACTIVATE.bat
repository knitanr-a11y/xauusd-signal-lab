@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "CONFIG_DIR=%ROOT%\config\gold_late_transition_v1"
set "CONFIG=%CONFIG_DIR%\local_config.json"
set "EXAMPLE=%CONFIG_DIR%\local_config.example.json"
set "PY=%LOCALAPPDATA%\xauusd_signal_lab\gold_late_transition_v1_shadow\venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [BLOCKED] Run 01_INSTALL.bat first.
  pause
  exit /b 2
)
if not exist "%CONFIG%" copy "%EXAMPLE%" "%CONFIG%" >nul
pushd "%ROOT%"
"%PY%" -m scripts.gold_late_transition_v1.shadow_runtime --config "%CONFIG%" bootstrap --activate
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" (
  echo [BLOCKED] Challenger bootstrap failed. Review the error above.
  pause
  exit /b %RC%
)
echo [OK] No-backfill Challenger prospective shadow activated.
pause
exit /b 0
