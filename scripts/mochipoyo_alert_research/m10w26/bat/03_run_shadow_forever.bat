@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "CORE=scripts\mochipoyo_alert_research\m10w26\python\m10w26_runtime.py"
set "OPERATOR=scripts\mochipoyo_alert_research\m10w26\python\run_m10w26_private_snapshot.py"
if not exist "%CORE%" goto :missing
if not exist "%OPERATOR%" goto :missing

python -c "import ast,pathlib; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8')) for p in (r'%CORE%',r'%OPERATOR%')]"
if errorlevel 1 (
  echo [M10W26 LOOP BLOCKED] Python syntax preflight failed.
  pause
  exit /b 2
)

echo ============================================================
echo M10W26 MMO1 CAUSAL-NEITHER FRESH PROSPECTIVE SHADOW
echo BOUNDED CSV PRIVATE VERIFIED SNAPSHOT - AUDIT ONLY
echo ============================================================
echo.
echo Keep this window OPEN.
echo Keep collector, M7C, M8C and all seven existing V4 loops RUNNING.
echo BAT01 must have passed exactly once. NEVER rerun BAT01 after initialization.
echo M10W26 is audit-only: Discord OFF / MT5 orders OFF / live gate OFF.
echo Formula, thresholds, causal NEITHER definition and 240-minute horizon are frozen.
echo Stop safely with 04_stop_shadow_forever.bat.
echo.

python "%OPERATOR%" forever --interval-seconds 60
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [M10W26 LOOP STOPPED] Normal STOP-file request completed.
) else (
  echo [M10W26 LOOP BLOCKED] exit code %RC%.
  echo Do not reset/reinitialize M10W26. Send this full screen and latest M10W26 log/status to ChatGPT.
)
echo Existing loops, runtimes and starts remain unchanged.
pause
exit /b %RC%

:missing
echo [M10W26 LOOP BLOCKED] Required implementation files are missing.
if not exist "%CORE%" echo MISSING: %CORE%
if not exist "%OPERATOR%" echo MISSING: %OPERATOR%
echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
echo Do not rerun BAT01 if M10W26 was already initialized.
pause
exit /b 2
