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
  echo [M10W34 INIT BLOCKED] Python syntax preflight failed. No start was created.
  pause
  exit /b 2
)

echo ============================================================
echo M10W34 SNDX1 FRESH START - INITIALIZE ONCE - AUDIT ONLY
echo ============================================================
echo Keep all existing eight loops and collector/M7C/M8C running.
echo This first audits six causal coverage families and the frozen SNDX1 feature engine.
echo It creates only a new M10W34 immutable MT5-server start after all prestart checks pass.
echo After INIT PASS, NEVER run this BAT again. Restart M10W34 only with BAT03.
echo.
python "%OPERATOR%" initialize
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [M10W34 INIT PASS] Start 03_run_shadow_forever.bat next.
) else (
  echo [M10W34 INIT BLOCKED] Do not reset, delete, edit or blindly retry. Send the full screen.
)
pause
exit /b %RC%

:missing
echo [M10W34 INIT BLOCKED] Required files are missing.
if not exist "%RUNTIME%" echo MISSING: %RUNTIME%
if not exist "%OPERATOR%" echo MISSING: %OPERATOR%
echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
pause
exit /b 2
