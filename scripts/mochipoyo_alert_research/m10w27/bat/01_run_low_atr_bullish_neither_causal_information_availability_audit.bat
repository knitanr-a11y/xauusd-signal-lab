@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "RUNNER=scripts\mochipoyo_alert_research\m10w27\python\run_m10w27_low_atr_bullish_neither_causal_information_availability_audit.py"
if not exist "%RUNNER%" (
  echo [M10W27 BLOCKED] Missing runner: %RUNNER%
  echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
  pause
  exit /b 2
)

python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%RUNNER%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [M10W27 BLOCKED] Python syntax preflight failed.
  pause
  exit /b 2
)

echo ============================================================
echo M10W27 LOW-ATR BULLISH CAUSAL-NEITHER INFORMATION AUDIT
echo OUTCOME BLIND / READ ONLY / GOLD XAUUSD ONLY
echo ============================================================
echo.
echo Keep collector, M7C, M8C and all eight private-snapshot loops running unchanged.
echo M10W26 BAT01 is permanently forbidden. Do not stop or modify M10W26.
echo This stage does NOT calculate returns, PF, PnL, labels or future paths.
echo It does NOT create an entry formula or choose a feature threshold.
echo.

python "%RUNNER%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W27\LATEST"
  echo [M10W27 PASS] Opening LATEST output folder.
  if exist "%LATEST%" start "" explorer "%LATEST%"
  echo Upload only 99_UPLOAD_PACKAGE.zip from M10W27 LATEST.
) else (
  echo [M10W27 BLOCKED] Do not alter formulas, thresholds, runtimes, starts, locks, snapshots or journals.
  echo Send this full screen to ChatGPT.
)
pause
exit /b %RC%
