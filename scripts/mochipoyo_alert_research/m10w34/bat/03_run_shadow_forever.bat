@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"
set "RUNTIME=scripts\mochipoyo_alert_research\m10w34\python\m10w34_runtime.py"
set "OPERATOR=scripts\mochipoyo_alert_research\m10w34\python\run_m10w34_private_snapshot.py"
if not exist "%RUNTIME%" goto :missing
if not exist "%OPERATOR%" goto :missing
python -c "import ast,pathlib; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8')) for p in (r'%RUNTIME%',r'%OPERATOR%')]"
if errorlevel 1 (
  echo [M10W34 LOOP BLOCKED] Python syntax preflight failed.
  pause
  exit /b 2
)
echo ============================================================
echo M10W34 SNDX1 FRESH PROSPECTIVE SHADOW - AUDIT ONLY
echo BOUNDED CSV PRIVATE VERIFIED SNAPSHOT
echo ============================================================
echo Keep this window OPEN. Keep all existing eight loops running.
echo BAT01 must have passed exactly once and must never be rerun.
echo Discord OFF / MT5 orders OFF / live-final gate OFF.
echo Stop normally only with BAT04.
echo.
python "%OPERATOR%" forever --interval-seconds 60
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" (
  echo [M10W34 LOOP STOPPED] Normal STOP-file request completed.
) else (
  echo [M10W34 LOOP BLOCKED] exit code %RC%. Do not reset or reinitialize.
)
pause
exit /b %RC%

:missing
echo [M10W34 LOOP BLOCKED] Required files are missing.
if not exist "%RUNTIME%" echo MISSING: %RUNTIME%
if not exist "%OPERATOR%" echo MISSING: %OPERATOR%
pause
exit /b 2
