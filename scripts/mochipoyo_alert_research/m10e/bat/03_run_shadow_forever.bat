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
if errorlevel 1 goto :syntax

echo ============================================================
echo M10E H1 Baseline vs Compound-Filter Shadow - FOREVER
echo BOUNDED CSV V4 - PRIVATE VERIFIED SNAPSHOT - PRESERVED START
echo ============================================================
echo.
echo Shared journals are adapter-write-only; M10E reads its private verified snapshot.
echo Audit only. Do NOT rerun BAT01.
echo.
python "%V4%" --loop M10E --interval-seconds 60 --compat-process-marker m10e_runtime.py
set "RC=%ERRORLEVEL%"
echo.
echo M10E loop exited with code %RC%.
if not "%RC%"=="0" echo Send the full screen output to ChatGPT. Do NOT reinitialize.
pause
exit /b %RC%

:syntax
echo [STOP] M10E V4 snapshot syntax preflight failed. Do not run BAT01.
pause
exit /b 2

:missing
echo [STOP] M10E REQUIRED V4 FILES ARE MISSING
if not exist "%ADAPTER%" echo MISSING: %ADAPTER%
if not exist "%INTEGRITY%" echo MISSING: %INTEGRITY%
if not exist "%RUNNER%" echo MISSING: %RUNNER%
if not exist "%V4%" echo MISSING: %V4%
echo Fetch/Pull branch feature/mochipoyo-alert-research. Do not run BAT01.
pause
exit /b 2
