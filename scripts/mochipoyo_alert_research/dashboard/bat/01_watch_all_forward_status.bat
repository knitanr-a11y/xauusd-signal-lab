@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "DASHBOARD=scripts\mochipoyo_alert_research\dashboard\python\forward_status_dashboard_v2.py"
if not exist "%DASHBOARD%" (
  echo [DASHBOARD BLOCKED] Missing: %DASHBOARD%
  echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
  pause
  exit /b 2
)

python -X utf8 -c "import ast,pathlib; ast.parse(pathlib.Path(r'%DASHBOARD%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [DASHBOARD BLOCKED] Python syntax preflight failed.
  echo No monitor, runtime, start, lock, journal, or output was changed.
  pause
  exit /b 2
)

title MOCHIPOYO M9V+ READ-ONLY STATUS DASHBOARD V2
mode con: cols=170 lines=42 >nul 2>&1

echo ============================================================
echo MOCHIPOYO M9V+ FORWARD STATUS DASHBOARD V2 - READ ONLY
echo ============================================================
echo Shows M9V, M9Y, M10B, M10E, M10P, M10P2, M10W19, M10W26, and M10W34.
echo Refreshes every 60 seconds. Ctrl+C closes only this dashboard.
echo PID or count null/missing values are displayed safely and never stop the remaining rows.
echo It never initializes, stops, restarts, resets, edits, deletes, tunes, sends Discord, or places MT5 orders.
echo.

python -X utf8 "%DASHBOARD%" --interval-seconds 60
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo [DASHBOARD CLOSED] Existing monitor windows remain unchanged.
) else (
  echo [DASHBOARD REVIEW] Exit code %RC%.
  echo Do not reset, stop, restart, edit, or delete anything. Send this full screen to ChatGPT.
)
pause
exit /b %RC%
