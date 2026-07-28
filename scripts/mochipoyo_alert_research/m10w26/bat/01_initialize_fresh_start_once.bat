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
  echo [M10W26 INIT BLOCKED] Python syntax preflight failed.
  echo No start or runtime was created.
  pause
  exit /b 2
)

echo ============================================================
echo M10W26 MMO1 CAUSAL-NEITHER FRESH START - INITIALIZE ONCE
echo AUDIT ONLY / DISCORD OFF / MT5 ORDER OFF / LIVE GATE OFF
echo ============================================================
echo.
echo Keep the existing seven V4 loops and collector/M7C/M8C running.
echo This creates a new M10W26-only immutable start from the current verified M1 frontier.
echo It does not change any existing runtime, start, monitor, formula or threshold.
echo After INIT PASS, NEVER run this BAT again. Restart M10W26 only with BAT03.
echo.

python "%OPERATOR%" initialize
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [M10W26 INIT PASS] Start 03_run_shadow_forever.bat next and keep that window open.
) else (
  echo [M10W26 INIT BLOCKED] Do not delete/reset anything. Send this full screen to ChatGPT.
)
pause
exit /b %RC%

:missing
echo [M10W26 INIT BLOCKED] Required implementation files are missing.
if not exist "%CORE%" echo MISSING: %CORE%
if not exist "%OPERATOR%" echo MISSING: %OPERATOR%
echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
echo No start or runtime was created.
pause
exit /b 2
