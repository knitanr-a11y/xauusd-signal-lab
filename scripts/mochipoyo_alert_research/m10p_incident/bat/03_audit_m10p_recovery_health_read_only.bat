@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "AUDIT=scripts\mochipoyo_alert_research\m10p_incident\python\audit_m10p_recovery_health.py"
if not exist "%AUDIT%" (
  echo [M10P RECOVERY HEALTH BLOCKED] Missing: %AUDIT%
  echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
  pause
  exit /b 2
)

python -X utf8 -c "import ast,pathlib; ast.parse(pathlib.Path(r'%AUDIT%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [M10P RECOVERY HEALTH BLOCKED] Python syntax preflight failed.
  echo No monitor, runtime, start, lock, state, journal, snapshot, Discord or MT5 order was changed.
  pause
  exit /b 2
)

 echo ============================================================
 echo M10P PRESERVED-START RECOVERY HEALTH AUDIT - READ ONLY
 echo ============================================================
 echo Run this only after the recovery window shows at least one [M10P PASS].
 echo Keep the recovery window and the other eight monitors running.
 echo.

python -X utf8 "%AUDIT%"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [M10P RECOVERY HEALTH REVIEW] Exit code %RC%.
  echo Do not run BAT01, reset, delete a lock, or restart anything.
  pause
  exit /b %RC%
)

set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10P_RECOVERY_HEALTH\LATEST"
echo.
echo [M10P RECOVERY HEALTH PASS] Upload only:
echo %OUT%\99_UPLOAD_PACKAGE.zip
start "" explorer "%OUT%"
pause
exit /b 0
