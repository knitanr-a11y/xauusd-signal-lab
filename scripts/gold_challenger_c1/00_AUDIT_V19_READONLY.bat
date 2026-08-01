@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow"
set "CONFIG=%STATE%\local_config.json"
set "PY=%STATE%\venv\Scripts\python.exe"
set "OUT=%USERPROFILE%\Desktop\challenger_v19_readonly_audit.txt"
if not exist "%PY%" (
  echo [BLOCKED] Run 01_INSTALL_SHADOW.bat first.
  pause
  exit /b 2
)
if not exist "%CONFIG%" (
  echo [BLOCKED] Challenger local_config.json is missing: %CONFIG%
  pause
  exit /b 2
)
pushd "%ROOT%"
"%PY%" -m scripts.gold_challenger_c1.audit_v19_runtime --config "%CONFIG%" > "%OUT%" 2>&1
set "RC=%ERRORLEVEL%"
popd
echo [READ-ONLY] Audit written to:
echo %OUT%
start "" notepad "%OUT%"
pause
exit /b %RC%
