@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE=%LOCALAPPDATA%\xauusd_signal_lab\gold_scalp_state_survival_shadow"
set "VENV=%STATE%\venv"
if not exist "%STATE%" mkdir "%STATE%"
if not exist "%VENV%\Scripts\python.exe" (
  py -3.12 -m venv "%VENV%" 2>nul || py -3 -m venv "%VENV%" 2>nul || python -m venv "%VENV%"
)
if not exist "%VENV%\Scripts\python.exe" (
  echo [BLOCKED] Python venv creation failed.
  pause
  exit /b 2
)
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%VENV%\Scripts\python.exe" -m pip install -r "%ROOT%\scripts\gold_scalp_state_survival_shadow\requirements.txt"
if errorlevel 1 goto :fail
pushd "%ROOT%"
"%VENV%\Scripts\python.exe" -m compileall scripts\gold_scalp_state_survival_shadow tests\gold_scalp_state_survival_shadow
if errorlevel 1 goto :fail_pop
"%VENV%\Scripts\python.exe" -m pytest -q tests\gold_scalp_state_survival_shadow
if errorlevel 1 goto :fail_pop
popd
echo.
echo [OK] State Survival Shadow environment and tests are ready.
pause
exit /b 0
:fail_pop
popd
:fail
echo.
echo [BLOCKED] Installation or verification failed.
pause
exit /b 2
