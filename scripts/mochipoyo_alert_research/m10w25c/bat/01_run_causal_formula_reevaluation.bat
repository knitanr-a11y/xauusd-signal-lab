@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "RUNNER=scripts\mochipoyo_alert_research\m10w25c\python\run_m10w25c_causal_formula_reevaluation.py"
if not exist "%RUNNER%" (
  echo [M10W25C BLOCKED] runner is missing: %RUNNER%
  echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
  echo Do not run BAT01 for M9V/M9Y/M10P/M10P2/M10W19 or change any start.
  pause
  exit /b 2
)

python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%RUNNER%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [M10W25C BLOCKED] Python syntax preflight failed.
  pause
  exit /b 2
)

echo ============================================================
echo M10W25C - CAUSAL NEITHER EXACT FROZEN FORMULA REEVALUATION
echo AUDIT ONLY - NO START / NO MONITOR CHANGE / NO DISCORD / NO MT5 ORDER
echo ============================================================
echo.
echo Keep the seven V4 bounded-adapter loops RUNNING.
echo This reads only frozen M10W24B and M10W25B artifacts.
echo It verifies exact SHA256 values and fails closed on any mismatch.
echo It does not tune formulas, thresholds or the four-hour horizon.
echo.

python "%RUNNER%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [M10W25C PASS] Opening LATEST output folder.
  start "" "%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W25C\LATEST"
) else (
  echo [M10W25C BLOCKED] Do not initialize/reset anything. Send this screen to ChatGPT.
)
pause
exit /b %RC%
