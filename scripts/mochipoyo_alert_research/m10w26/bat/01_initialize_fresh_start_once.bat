@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "CORE=scripts\mochipoyo_alert_research\m10w26\python\m10w26_runtime.py"
set "COREV2=scripts\mochipoyo_alert_research\m10w26\python\m10w26_runtime_v2.py"
set "BASEOP=scripts\mochipoyo_alert_research\m10w26\python\run_m10w26_private_snapshot.py"
set "OPERATOR=scripts\mochipoyo_alert_research\m10w26\python\run_m10w26_private_snapshot_v2.py"
if not exist "%CORE%" goto :missing
if not exist "%COREV2%" goto :missing
if not exist "%BASEOP%" goto :missing
if not exist "%OPERATOR%" goto :missing

python -c "import ast,pathlib; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8')) for p in (r'%CORE%',r'%COREV2%',r'%BASEOP%',r'%OPERATOR%')]"
if errorlevel 1 (
  echo [M10W26 INIT BLOCKED] Python syntax preflight failed.
  echo No start or runtime was created.
  pause
  exit /b 2
)

echo ============================================================
echo M10W26 MMO1 CAUSAL-NEITHER FRESH START V2 - INITIALIZE ONCE
echo PRESTART SIX-FAMILY CAUSAL ENGINE AUDIT REQUIRED
echo AUDIT ONLY / DISCORD OFF / MT5 ORDER OFF / LIVE GATE OFF
echo ============================================================
echo.
echo Keep the existing seven V4 loops and collector/M7C/M8C running.
echo Before writing a start, V2 runs all six M10W25 causal coverage families on a verified private snapshot.
echo This creates a new M10W26-only immutable start only after that prestart audit passes.
echo It does not change any existing runtime, start, monitor, formula or threshold.
echo After INIT PASS, NEVER run this BAT again. Restart M10W26 only with BAT03.
echo.

python "%OPERATOR%" initialize
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [M10W26 INIT PASS] Start 03_run_shadow_forever.bat next and keep that window open.
) else (
  echo [M10W26 INIT BLOCKED] No reset or cleanup is authorized. Send this full screen to ChatGPT.
)
pause
exit /b %RC%

:missing
echo [M10W26 INIT BLOCKED] Required V2 implementation files are missing.
if not exist "%CORE%" echo MISSING: %CORE%
if not exist "%COREV2%" echo MISSING: %COREV2%
if not exist "%BASEOP%" echo MISSING: %BASEOP%
if not exist "%OPERATOR%" echo MISSING: %OPERATOR%
echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
echo No start or runtime was created.
pause
exit /b 2
