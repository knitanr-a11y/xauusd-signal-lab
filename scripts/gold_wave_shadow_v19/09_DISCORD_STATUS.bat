@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "CONFIG=%ROOT%\config\gold_wave_shadow_v19\local_config.json"
set "PY=%LOCALAPPDATA%\xauusd_signal_lab\gold_v19_shadow\venv\Scripts\python.exe"
if not exist "%PY%" exit /b 2
if not exist "%CONFIG%" exit /b 2
pushd "%ROOT%"
"%PY%" -m scripts.gold_wave_shadow_v19.discord_notifier --config "%CONFIG%" status
set "RC=%ERRORLEVEL%"
popd
pause
exit /b %RC%
