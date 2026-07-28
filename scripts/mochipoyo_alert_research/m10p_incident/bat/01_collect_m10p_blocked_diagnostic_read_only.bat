@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "COLLECTOR=scripts\mochipoyo_alert_research\m10p_incident\python\collect_m10p_blocked_diagnostic.py"
if not exist "%COLLECTOR%" (
  echo [M10P DIAGNOSTIC BLOCKED] Missing: %COLLECTOR%
  echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
  pause
  exit /b 2
)

python -X utf8 -c "import ast,pathlib; ast.parse(pathlib.Path(r'%COLLECTOR%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [M10P DIAGNOSTIC BLOCKED] Python syntax preflight failed.
  echo No monitor, runtime, start, lock, journal, snapshot, output, Discord, or MT5 order was changed.
  pause
  exit /b 2
)

echo ============================================================
echo M10P BLOCKED DIAGNOSTIC COLLECTOR - READ ONLY
echo ============================================================
echo This does NOT initialize, start, stop, restart, reset, edit, or delete M10P.
echo It only reads the blocked status/log/runtime/state/start/LATEST evidence
 echo and writes a separate M10P_BLOCKED_DIAGNOSTIC upload package.
echo Keep the other eight monitor windows running unchanged.
echo.

python -X utf8 "%COLLECTOR%"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [M10P DIAGNOSTIC REVIEW] Exit code %RC%.
  echo Do not run M10P BAT01, do not restart M10P, and do not edit/delete anything.
  pause
  exit /b %RC%
)

set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10P_BLOCKED_DIAGNOSTIC\LATEST"
echo.
echo [M10P DIAGNOSTIC PASS] Upload only:
echo %OUT%\99_UPLOAD_PACKAGE.zip
start "" explorer "%OUT%"
pause
exit /b 0
