@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "RUNNER=scripts\mochipoyo_alert_research\m10w29\python\run_low_atr_micro_eval.py"
if not exist "%RUNNER%" (
  echo [M10W29 BLOCKED] Missing: %RUNNER%
  echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
  pause
  exit /b 2
)

python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%RUNNER%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [M10W29 BLOCKED] Python syntax preflight failed.
  pause
  exit /b 2
)

echo ============================================================
echo M10W29 LOW-ATR CAUSAL-NEITHER PREREGISTERED EVALUATION
echo AUDIT ONLY - KEEP ALL EIGHT LOOPS RUNNING
echo ============================================================
echo.
echo This evaluates all three frozen M10W28 formulas without tuning.
echo No existing runtime, start, threshold, Discord or MT5 order is changed.
echo.
python "%RUNNER%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W29\LATEST"
  if exist "%LATEST%" start "" explorer "%LATEST%"
  echo [M10W29 PASS] Upload 99_UPLOAD_PACKAGE.zip from M10W29 LATEST.
) else (
  echo [M10W29 BLOCKED] Do not tune, reset or modify any monitor. Send this screen to ChatGPT.
)
pause
exit /b %RC%
