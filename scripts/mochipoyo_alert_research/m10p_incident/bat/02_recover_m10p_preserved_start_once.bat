@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "RECOVERY=scripts\mochipoyo_alert_research\m10p_incident\python\recover_m10p_preserved_start.py"
if not exist "%RECOVERY%" (
  echo [M10P RECOVERY BLOCKED] Missing: %RECOVERY%
  echo Confirm branch feature/mochipoyo-alert-research, Fetch origin, and Pull origin.
  pause
  exit /b 2
)

python -X utf8 -c "import ast,pathlib; ast.parse(pathlib.Path(r'%RECOVERY%').read_text(encoding='utf-8'))"
if errorlevel 1 (
  echo [M10P RECOVERY BLOCKED] Python syntax preflight failed.
  echo No runtime, start, state, lock, journal, snapshot, evidence, Discord, or MT5 order was changed.
  pause
  exit /b 2
)

title M10P PRESERVED-START RECOVERY - AUDIT ONLY
mode con: cols=150 lines=42 >nul 2>&1

echo ======================================================================
echo M10P PRESERVED-START RECOVERY AFTER STATUS PUBLICATION RACE
echo ======================================================================
echo This is NOT BAT01 and does not initialize or reset M10P.
echo It verifies the immutable start 2026.07.24 23:56:00, runtime, state,
echo start receipt, BLOCKED cause, absent lock, absent old process and LATEST evidence.
echo It then resumes only M10P from the same preserved start.
echo Keep the other eight healthy monitor windows running unchanged.
echo Do not close this recovery window after the first PASS.
echo ======================================================================
echo.

python -X utf8 "%RECOVERY%"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo [M10P RECOVERY CLOSED] The loop ended normally. Send this full screen before any action.
) else (
  echo [M10P RECOVERY REVIEW] Exit code %RC%.
  echo Do not run BAT01, do not delete a lock, and do not edit/reset runtime or start.
)
pause
exit /b %RC%
