@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "ADAPTER=scripts\mochipoyo_alert_research\common\python\bounded_csv_source_adapter.py"
set "INTEGRITY=scripts\mochipoyo_alert_research\common\python\bounded_csv_journal_integrity.py"
set "RUNNER=scripts\mochipoyo_alert_research\common\python\run_bounded_adapter_loop.py"
set "V4=scripts\mochipoyo_alert_research\common\python\run_bounded_adapter_loop_v4.py"

if not exist "%ADAPTER%" goto :missing
if not exist "%INTEGRITY%" goto :missing
if not exist "%RUNNER%" goto :missing
if not exist "%V4%" goto :missing

python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%V4%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [M9Y LOOP BLOCKED] V4 snapshot syntax preflight failed.
  echo Do not run BAT01 or change the frozen start.
  pause
  exit /b 2
)

echo ============================================================
echo M9Y GOLD Payoff Fresh Prospective Shadow - PERSISTENT
echo BOUNDED CSV V4 - PRIVATE VERIFIED SNAPSHOT - PRESERVED START
echo ============================================================
echo.
echo Keep this window OPEN. Keep M8C / M7C / collector / M9V running in parallel.
echo Shared journals are adapter-write-only; M9Y reads its private verified snapshot.
echo Audit-only: Discord OFF / MT5 orders OFF / live gate OFF.
echo Transient Windows file contention waits without resetting the start.
echo Stop safely with 04_stop_shadow_forever.bat.
echo Do NOT rerun BAT01.
echo.

python "%V4%" --loop M9Y --interval-seconds 60 --compat-process-marker run_m9y_shadow_forever_safe.py
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo [M9Y LOOP STOPPED] normal stop.) else (echo [M9Y LOOP BLOCKED] exit code %RC%. Send full output to ChatGPT.)
echo Existing M8C/M7C/M9V, runtime manifest, and frozen start remain unchanged.
pause
exit /b %RC%

:missing
echo [M9Y LOOP BLOCKED] REQUIRED V4 FILES ARE MISSING
if not exist "%ADAPTER%" echo MISSING: %ADAPTER%
if not exist "%INTEGRITY%" echo MISSING: %INTEGRITY%
if not exist "%RUNNER%" echo MISSING: %RUNNER%
if not exist "%V4%" echo MISSING: %V4%
echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
echo Do not run BAT01 or change any runtime/start.
pause
exit /b 2
