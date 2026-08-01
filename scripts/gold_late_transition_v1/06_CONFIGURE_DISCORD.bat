@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "CONFIG=%ROOT%\config\gold_late_transition_v1\local_config.json"
set "PY=%LOCALAPPDATA%\xauusd_signal_lab\gold_late_transition_v1_shadow\venv\Scripts\python.exe"
if not exist "%PY%" exit /b 2
if not exist "%CONFIG%" exit /b 2
pushd "%ROOT%"
"%PY%" -m scripts.gold_late_transition_v1.discord_notifier --config "%CONFIG%" configure
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" exit /b %RC%
echo [OK] Challenger Discord references the existing local V19 webhook. The secret was not copied.
endlocal
