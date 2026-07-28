@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"
set "AUDIT=scripts\mochipoyo_alert_research\m10w34\python\audit_m10w34_initial_health.py"
if not exist "%AUDIT%" (
  echo [M10W34 HEALTH BLOCKED] Missing: %AUDIT%
  pause
  exit /b 2
)
python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%AUDIT%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [M10W34 HEALTH BLOCKED] Python syntax preflight failed.
  pause
  exit /b 2
)
echo M10W34 INITIAL HEALTH AUDIT - READ ONLY
python "%AUDIT%"
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" (
  set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W34_INITIAL_HEALTH\LATEST"
  if exist "%LATEST%" start "" explorer "%LATEST%"
  echo Upload only 99_UPLOAD_PACKAGE.zip from M10W34_INITIAL_HEALTH LATEST.
) else (
  echo [M10W34 HEALTH REVIEW] Do not reset, stop, edit or delete anything.
)
pause
exit /b %RC%
