@echo off
setlocal EnableExtensions DisableDelayedExpansion

for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"
if not exist "config\mochipoyo_alert_research\current_state_20260728.json" (
  echo [STOP] Repository root could not be resolved from this BAT.
  echo BAT:  %~f0
  echo ROOT: %REPO_ROOT%
  pause
  exit /b 2
)

set "AUDIT=scripts\mochipoyo_alert_research\recovery\python\audit_bounded_adapter_restart_health.py"
set "ADAPTER=scripts\mochipoyo_alert_research\common\python\bounded_csv_source_adapter.py"
set "INTEGRITY=scripts\mochipoyo_alert_research\common\python\bounded_csv_journal_integrity.py"
if not exist "%AUDIT%" goto :missing
if not exist "%ADAPTER%" goto :missing
if not exist "%INTEGRITY%" goto :missing

echo ============================================================
echo MOCHIPOYO - BOUNDED ADAPTER RESTART HEALTH AUDIT
echo READ ONLY - ALL SEVEN LOOPS
echo ============================================================
echo.
echo Run this only after starting BAT03 in this exact order:
echo M9V, M9Y, M10B, M10E, M10P, M10P2, M10W19.
echo Allow each window to complete at least one successful cycle first.
echo.
echo This audit does NOT start or stop loops, remove locks, update journals,
echo reset runtimes, change starts, send Discord, or place MT5 orders.
echo.

python "%AUDIT%"
set "RC=%ERRORLEVEL%"
set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\BOUNDED_CSV_SOURCE_ADAPTER_RESTART_HEALTH\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"

echo.
if "%RC%"=="0" (
  echo [PASS] All seven loops are running with at least one successful bounded-adapter cycle.
) else if "%RC%"=="3" (
  echo [REVIEW REQUIRED] At least one loop is not yet healthy or is waiting on a transient source condition.
) else (
  echo [STOP] Health audit could not complete.
)
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened LATEST folder.
echo Do not run BAT01 or change any prospective start.
pause
exit /b %RC%

:missing
echo [STOP] Required restart-health audit files are missing.
if not exist "%AUDIT%" echo MISSING: %AUDIT%
if not exist "%ADAPTER%" echo MISSING: %ADAPTER%
if not exist "%INTEGRITY%" echo MISSING: %INTEGRITY%
echo Confirm branch feature/mochipoyo-alert-research, then Fetch/Pull again.
echo Do not run BAT01 or delete any lock/runtime/adapter file manually.
pause
exit /b 2
