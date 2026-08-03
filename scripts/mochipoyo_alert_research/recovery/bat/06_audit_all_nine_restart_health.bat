@echo off
setlocal EnableExtensions DisableDelayedExpansion

for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"
if not exist "config\mochipoyo_alert_research\current_state_20260729.json" (
  echo [STOP] Repository root could not be resolved from this BAT.
  echo BAT:  %~f0
  echo ROOT: %REPO_ROOT%
  echo Do not run BAT01, delete locks, or change any prospective start.
  pause
  exit /b 2
)

set "AUDIT=scripts\mochipoyo_alert_research\recovery\python\audit_all_nine_restart_health.py"
if not exist "%AUDIT%" (
  echo [STOP] All-nine restart-health audit is missing:
  echo %AUDIT%
  echo Confirm branch feature/mochipoyo-alert-research, then Fetch/Pull again.
  pause
  exit /b 2
)

python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%AUDIT%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [STOP] All-nine restart-health audit syntax preflight failed.
  echo No loop, lock, runtime or start was changed.
  pause
  exit /b 2
)

echo ============================================================
echo MOCHIPOYO - ALL NINE RESTART HEALTH AUDIT
echo READ ONLY / AUDIT ONLY
echo ============================================================
echo.
echo Run this after BAT03 restart in this exact order:
echo M9V, M9Y, M10B, M10E, M10P, M10P2, M10W19, M10W26, M10W34.
echo Allow every window to complete at least one successful cycle.
echo.
echo This audit does NOT start/stop loops, remove locks, edit runtimes,
echo reset starts, update journals/snapshots, send Discord, or place MT5 orders.
echo.

python "%AUDIT%"
set "RC=%ERRORLEVEL%"
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\ALL_NINE_RESTART_HEALTH\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"

echo.
if "%RC%"=="0" (
  echo [PASS] All nine forward loops are healthy.
) else if "%RC%"=="3" (
  echo [REVIEW REQUIRED] At least one loop is not yet healthy.
) else (
  echo [STOP] All-nine health audit could not complete.
)
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened LATEST folder.
echo Do not run BAT01, reset starts, or delete locks manually.
pause
exit /b %RC%
