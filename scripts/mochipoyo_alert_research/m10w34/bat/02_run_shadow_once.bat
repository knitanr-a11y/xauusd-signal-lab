@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"
set "OPERATOR=scripts\mochipoyo_alert_research\m10w34\python\run_m10w34_private_snapshot.py"
if not exist "%OPERATOR%" (
  echo [M10W34 ONCE BLOCKED] Missing: %OPERATOR%
  pause
  exit /b 2
)
echo M10W34 SNDX1 SHADOW - ONE CYCLE - AUDIT ONLY
python "%OPERATOR%" once
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" (
  set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W34\LATEST"
  if exist "%LATEST%" start "" explorer "%LATEST%"
) else (
  echo [M10W34 ONCE BLOCKED] Do not reset or reinitialize.
)
pause
exit /b %RC%
