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
echo M10B GOLD Multi-Timeframe Payoff Fresh Shadow - FOREVER
echo BOUNDED CSV V4 - PRIVATE VERIFIED SNAPSHOT - PRESERVED START
echo ============================================================
echo Keep collector / M7C / M8C / M9V / M9Y running unchanged.
echo Shared journals are adapter-write-only; M10B reads its private verified snapshot.
echo Do NOT rerun BAT01.
echo.
python "%V4%" --loop M10B --interval-seconds 60 --compat-process-marker m10b_runtime.py
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10B loop was blocked. Do not reset/reinitialize anything.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)
echo.
echo [DONE] M10B loop stopped gracefully.
pause
exit /b 0

:syntax
echo [STOP] M10B V4 snapshot syntax preflight failed. Do not run BAT01.
pause
exit /b 2

:missing
echo [STOP] M10B REQUIRED V4 FILES ARE MISSING
if not exist "%ADAPTER%" echo MISSING: %ADAPTER%
if not exist "%INTEGRITY%" echo MISSING: %INTEGRITY%
if not exist "%RUNNER%" echo MISSING: %RUNNER%
if not exist "%V4%" echo MISSING: %V4%
echo Fetch/Pull branch feature/mochipoyo-alert-research. Do not run BAT01.
pause
exit /b 2
