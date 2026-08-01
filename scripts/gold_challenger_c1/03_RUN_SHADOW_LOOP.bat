@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow"
set "CONFIG=%STATE%\local_config.json"
set "PY=%STATE%\venv\Scripts\python.exe"
if not exist "%PY%" exit /b 2
if not exist "%CONFIG%" exit /b 2
pushd "%ROOT%"
"%PY%" -m scripts.gold_challenger_c1.shadow_runtime --config "%CONFIG%" loop
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
