@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "CONFIG_DIR=%ROOT%\config\gold_wave_shadow_v19"
set "CONFIG=%CONFIG_DIR%\local_config.json"
set "EXAMPLE=%CONFIG_DIR%\local_config.example.json"
set "PY=%LOCALAPPDATA%\xauusd_signal_lab\gold_v19_shadow\venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [BLOCKED] Run 01_INSTALL.bat first.
  exit /b 2
)
if not exist "%CONFIG%" (
  copy "%EXAMPLE%" "%CONFIG%" >nul
  echo [ACTION REQUIRED] local_config.json was created.
  echo Replace every C:\REPLACE_ME path, save the file, then run this BAT again.
  start "" notepad "%CONFIG%"
  exit /b 2
)
findstr /C:"REPLACE_ME" "%CONFIG%" >nul && (
  echo [BLOCKED] local_config.json still contains REPLACE_ME.
  start "" notepad "%CONFIG%"
  exit /b 2
)
pushd "%ROOT%"
"%PY%" -m scripts.gold_wave_shadow_v19.shadow_runtime --config "%CONFIG%" bootstrap --activate
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" exit /b %RC%
echo [OK] No-backfill prospective shadow activated.
endlocal
