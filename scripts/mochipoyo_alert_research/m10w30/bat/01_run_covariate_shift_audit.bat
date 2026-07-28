@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "RUNNER=scripts\mochipoyo_alert_research\m10w30\python\run_low_atr_covariate_shift_audit.py"
if not exist "%RUNNER%" (
  echo [M10W30 BLOCKED] Missing runner: %RUNNER%
  echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
  pause
  exit /b 2
)

python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%RUNNER%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [M10W30 BLOCKED] Python syntax preflight failed.
  pause
  exit /b 2
)

echo ============================================================
echo M10W30 LOW-ATR POST-RESULT COVARIATE SHIFT DIAGNOSTIC
echo PRE-ENTRY FEATURES ONLY / AUDIT ONLY / NO CANDIDATE RESCUE
echo ============================================================
echo.
echo Keep collector, M7C, M8C and all eight loops running unchanged.
echo M10W26 BAT01 is permanently forbidden.
echo This reads only the M10W27 pre-entry feature rows.
echo It does not read returns, PF, PnL, win/loss labels or trade ledgers.
echo It cannot change or rescue any M10W29 formula, threshold, session, ATR boundary, horizon or exit.
echo.

python "%RUNNER%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W30\LATEST"
  echo [M10W30 PASS] Opening LATEST output folder.
  if exist "%LATEST%" start "" explorer "%LATEST%"
  echo Upload only 99_UPLOAD_PACKAGE.zip from M10W30 LATEST.
) else (
  echo [M10W30 BLOCKED] Do not tune, reset, delete or rerun blindly. Send this full screen to ChatGPT.
)
pause
exit /b %RC%
