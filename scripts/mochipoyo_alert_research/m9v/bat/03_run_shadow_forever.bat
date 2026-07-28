@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "ADAPTER=scripts\mochipoyo_alert_research\common\python\bounded_csv_source_adapter.py"
set "INTEGRITY=scripts\mochipoyo_alert_research\common\python\bounded_csv_journal_integrity.py"
set "RUNNER=scripts\mochipoyo_alert_research\common\python\run_bounded_adapter_loop.py"
set "BOOTSTRAP=scripts\mochipoyo_alert_research\common\python\m9v_bounded_start_bootstrap.py"
set "V4=scripts\mochipoyo_alert_research\common\python\run_bounded_adapter_loop_v4.py"

if not exist "%ADAPTER%" goto :missing
if not exist "%INTEGRITY%" goto :missing
if not exist "%RUNNER%" goto :missing
if not exist "%BOOTSTRAP%" goto :missing
if not exist "%V4%" goto :missing

python -c "import ast,pathlib; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8')) for p in (r'%BOOTSTRAP%',r'%V4%')]"
if errorlevel 1 (
  echo [M9V LOOP BLOCKED] V4 snapshot syntax preflight failed.
  echo Do not run BAT00/BAT01 or change the frozen start.
  pause
  exit /b 2
)

echo ============================================================
echo M9V GOLD Multi-Timeframe Prospective Shadow - PERSISTENT
echo BOUNDED CSV V4 - PRIVATE VERIFIED SNAPSHOT - IMMUTABLE START
echo ============================================================
echo.
echo Keep this window OPEN.
echo Keep M8C / M7C / genuine source collector RUNNING in parallel.
echo Shared journals are adapter-write-only; M9V reads its private verified snapshot.
echo The frozen runtime state-at-start is the authoritative bootstrap.
echo Old bounded-source head rows are NOT reconstructed or backfilled.
echo Transient Windows file contention waits without resetting the start.
echo Journal SHA256 plus genuine runtime/start/timestamp/overlap failures stop fail-closed.
echo Stop safely with 04_stop_shadow_forever.bat.
echo Do NOT rerun BAT00/BAT01.
echo.

python "%V4%" --loop M9V --interval-seconds 60 --compat-process-marker run_m9v_shadow_forever_safe
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo [M9V LOOP STOPPED] normal stop request or manual close.
) else (
  echo [M9V LOOP BLOCKED] exit code %RC%.
  echo Do not reset/reinitialize M9V. Send the full screen output and latest M9V log/status to ChatGPT.
)
echo M8C, M7C, collector, runtime manifest, and frozen start remain unchanged.
pause
exit /b %RC%

:missing
echo ============================================================
echo [M9V LOOP BLOCKED] REQUIRED V4 FILES ARE MISSING
echo ============================================================
if not exist "%ADAPTER%" echo MISSING: %ADAPTER%
if not exist "%INTEGRITY%" echo MISSING: %INTEGRITY%
if not exist "%RUNNER%" echo MISSING: %RUNNER%
if not exist "%BOOTSTRAP%" echo MISSING: %BOOTSTRAP%
if not exist "%V4%" echo MISSING: %V4%
echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
echo Do not run BAT00/BAT01 or change any runtime/start.
pause
exit /b 2
