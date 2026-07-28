@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "RUNNER=scripts\mochipoyo_alert_research\m10w31\python\run_scale_normalized_causal_information_audit.py"
if not exist "%RUNNER%" (
  echo [M10W31 BLOCKED] Missing runner: %RUNNER%
  echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
  pause
  exit /b 2
)

python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%RUNNER%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [M10W31 BLOCKED] Python syntax preflight failed.
  pause
  exit /b 2
)

echo ============================================================
echo M10W31 LOW-ATR SCALE-NORMALIZED CAUSAL INFORMATION AUDIT
echo OUTCOME BLIND / READ ONLY / NO ENTRY FORMULA
echo ============================================================
echo.
echo Keep collector, M7C, M8C and all eight loops running unchanged.
echo M10W26 BAT01 is permanently forbidden.
echo This uses the exact M10W27 7480-row decision-time cohort.
echo It computes only causal H1-ATR-normalized and already scale-free pre-entry features.
echo It does not read returns, PF, PnL, labels, trade ledgers or future paths.
echo It does not create a candidate or select a threshold.
echo.

python "%RUNNER%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W31\LATEST"
  echo [M10W31 PASS] Opening LATEST output folder.
  if exist "%LATEST%" start "" explorer "%LATEST%"
  echo Upload only 99_UPLOAD_PACKAGE.zip from M10W31 LATEST.
) else (
  echo [M10W31 BLOCKED] Do not tune, reset, edit, delete or retry blindly. Send this full screen to ChatGPT.
)
pause
exit /b %RC%
