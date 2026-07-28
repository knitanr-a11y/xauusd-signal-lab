@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "AUDIT=scripts\mochipoyo_alert_research\m10w34\python\audit_m10w34_checkpoint.py"
if not exist "%AUDIT%" (
  echo [M10W34 CHECKPOINT BLOCKED] Missing: %AUDIT%
  pause
  exit /b 2
)
python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%AUDIT%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [M10W34 CHECKPOINT BLOCKED] Python syntax preflight failed.
  pause
  exit /b 2
)

echo ============================================================
echo M10W34 READ-ONLY CHECKPOINT AUDIT
echo HEALTH + 20 / 60 / 120 RESOLVED REVIEW READINESS
echo ============================================================
echo Keep M10W34 and all existing loops running unchanged.
echo This does not initialize, restart, stop, reset, tune, promote, send Discord, or place MT5 orders.
echo.
python "%AUDIT%"
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" (
  set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W34_CHECKPOINT\LATEST"
  if exist "%LATEST%" start "" explorer "%LATEST%"
  echo Upload only 99_UPLOAD_PACKAGE.zip from M10W34_CHECKPOINT LATEST when a requested review gate is reached.
) else (
  echo [M10W34 CHECKPOINT REVIEW] Do not reset, stop, edit, delete, or retry blindly.
)
pause
exit /b %RC%
