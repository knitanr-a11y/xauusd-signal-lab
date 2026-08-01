@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow"
set "CONFIG=%STATE%\local_config.json"
set "PY=%STATE%\venv\Scripts\python.exe"
pushd "%ROOT%"
"%PY%" -m scripts.gold_challenger_c1.discord_notifier --config "%CONFIG%" status
set "RC=%ERRORLEVEL%"
popd
pause
exit /b %RC%
