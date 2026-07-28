@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "OPERATOR=scripts\mochipoyo_alert_research\recovery\python\stop_bounded_adapter_loops_for_v4_upgrade.py"
if not exist "%OPERATOR%" (
  echo [STOP] V4 upgrade stop operator is missing: %OPERATOR%
  echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
  echo Do not close loops forcibly, delete locks, run BAT01, or change starts.
  pause
  exit /b 2
)

python -c "import ast,pathlib; ast.parse(pathlib.Path(r'%OPERATOR%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [STOP] V4 upgrade stop operator syntax preflight failed.
  echo Do not close loops forcibly or delete locks.
  pause
  exit /b 2
)

echo ============================================================
echo MOCHIPOYO - GRACEFUL STOP FOR V4 PRIVATE SNAPSHOT UPGRADE
echo ============================================================
echo.
echo This requests normal STOP-file shutdown for M9V/M9Y/M10B/M10E/M10P/M10P2/M10W19.
echo It does NOT stop collector, M7C, M8C, MT5, or other loops.
echo It does NOT kill processes, delete locks, edit runtimes, or reset starts.
echo.
python "%OPERATOR%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP BLOCKED] Leave all evidence unchanged and send this screen to ChatGPT.
  pause
  exit /b %RC%
)
echo [STOP PASS] Fetch/Pull latest branch, then restart the seven BAT03 launchers in order.
pause
exit /b 0
