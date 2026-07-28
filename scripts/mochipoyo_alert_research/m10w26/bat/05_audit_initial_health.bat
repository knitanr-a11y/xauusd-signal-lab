@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "AUDIT=scripts\mochipoyo_alert_research\m10w26\python\audit_m10w26_initial_health.py"
if not exist "%AUDIT%" (
  echo [M10W26 HEALTH BLOCKED] Missing: %AUDIT%
  echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
  pause
  exit /b 2
)
python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%AUDIT%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [M10W26 HEALTH BLOCKED] Python syntax preflight failed.
  pause
  exit /b 2
)

echo ============================================================
echo M10W26 INITIAL PRIVATE-SNAPSHOT HEALTH AUDIT - READ ONLY
echo ============================================================
echo Keep M10W26 and all existing loops running.
echo This does not start, stop, reset, initialize or mutate any loop.
echo.
python "%AUDIT%"
set "RC=%ERRORLEVEL%"
echo.
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W26_INITIAL_HEALTH\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
if "%RC%"=="0" (
  echo [M10W26 HEALTH PASS] Upload only LATEST\99_UPLOAD_PACKAGE.zip.
) else (
  echo [M10W26 HEALTH REVIEW] Do not stop/reset/reinitialize. Upload the package if created and send this screen.
)
pause
exit /b %RC%
