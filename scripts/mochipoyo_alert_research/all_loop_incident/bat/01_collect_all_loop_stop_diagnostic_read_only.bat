@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul

for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "COLLECTOR=scripts\mochipoyo_alert_research\all_loop_incident\python\collect_all_loop_stop_diagnostic.py"
if not exist "%COLLECTOR%" (
  echo [ALL LOOP DIAGNOSTIC BLOCKED] Missing: %COLLECTOR%
  echo Confirm branch feature/mochipoyo-alert-research, then Fetch origin and Pull origin.
  pause
  exit /b 2
)

python -X utf8 -c "import ast,pathlib; ast.parse(pathlib.Path(r'%COLLECTOR%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [ALL LOOP DIAGNOSTIC BLOCKED] Python syntax preflight failed.
  echo No monitor, runtime, start, lock, journal, snapshot, CSV, Discord, or MT5 order was changed.
  pause
  exit /b 2
)

echo ============================================================
echo ALL LOOP STOP DIAGNOSTIC - READ ONLY
echo ============================================================
echo This does NOT initialize, start, stop, restart, reset, edit, or delete any loop.
echo It reads status, locks, process inventory, runtime JSON, summaries, and log tails only.
echo It writes only a separate ALL_LOOP_STOP_DIAGNOSTIC package.
echo.
echo Do NOT run BAT01, recovery BAT, taskkill, lock deletion, or manual runtime edits.
echo.

python -X utf8 "%COLLECTOR%"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [ALL LOOP DIAGNOSTIC REVIEW] Exit code %RC%.
  echo Stop here. Do not restart or initialize any loop.
  pause
  exit /b %RC%
)

set "OUT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\ALL_LOOP_STOP_DIAGNOSTIC\LATEST"
echo.
echo [ALL LOOP DIAGNOSTIC PASS] Upload only:
echo %OUT%\99_UPLOAD_PACKAGE.zip
start "" explorer "%OUT%"
pause
exit /b 0
