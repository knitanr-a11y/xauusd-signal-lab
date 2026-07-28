@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"
set "OPERATOR=scripts\mochipoyo_alert_research\m10w26\python\run_m10w26_private_snapshot.py"

if not exist "%OPERATOR%" (
  echo [M10W26 ONCE BLOCKED] Missing: %OPERATOR%
  pause
  exit /b 2
)

echo ============================================================
echo M10W26 MMO1 CAUSAL-NEITHER SHADOW - ONE CYCLE - AUDIT ONLY
echo ============================================================
echo Keep all existing loops running. BAT01 must already have passed exactly once.
echo.
python "%OPERATOR%" once
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" (
  set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W26\LATEST"
  if exist "%LATEST%" start "" explorer "%LATEST%"
) else (
  echo [M10W26 ONCE BLOCKED] Do not reset or reinitialize. Send this screen to ChatGPT.
)
pause
exit /b %RC%
