@echo off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STATE_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\gold_late_transition_v1_shadow"
set "VENV=%STATE_ROOT%\venv"
if not exist "%STATE_ROOT%" mkdir "%STATE_ROOT%"
where py >nul 2>&1 || (
  echo [BLOCKED] Python launcher 'py' was not found.
  exit /b 2
)
if not exist "%VENV%\Scripts\python.exe" (
  py -3.12 -m venv "%VENV%" || py -3 -m venv "%VENV%" || exit /b 2
)
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip || exit /b 2
"%VENV%\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt" || exit /b 2
echo [OK] GOLD Late Transition V1 shadow environment installed at:
echo %VENV%
endlocal
