@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "RUNNER=scripts\mochipoyo_alert_research\m10w33\python\run_scale_normalized_entry_eval.py"
if not exist "%RUNNER%" (
  echo [M10W33 BLOCKED] Missing runner: %RUNNER%
  echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
  pause
  exit /b 2
)

python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%RUNNER%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [M10W33 BLOCKED] Python syntax preflight failed.
  pause
  exit /b 2
)

echo ============================================================
echo M10W33 SCALE-NORMALIZED LOW-ATR ENTRY EVALUATION
echo PREREGISTERED / AUDIT ONLY / GOLD XAUUSD ONLY
echo ============================================================
echo.
echo Keep collector, M7C, M8C and all eight loops running unchanged.
echo M10W26 BAT01 is permanently forbidden. Do not stop or modify M10W26.
echo M10W29 families remain closed and are not rescued by this evaluation.
echo The three M10W32 formulas, thresholds, 240-minute horizon and one-position rule are frozen.
echo.

python "%RUNNER%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W33\LATEST"
  echo [M10W33 PASS] Opening LATEST output folder.
  if exist "%LATEST%" start "" explorer "%LATEST%"
  echo Upload only 99_UPLOAD_PACKAGE.zip from M10W33 LATEST.
) else (
  echo [M10W33 BLOCKED] Do not alter formulas, thresholds, runtimes, starts, locks, snapshots or journals.
  echo Send this full screen to ChatGPT.
)
pause
exit /b %RC%
