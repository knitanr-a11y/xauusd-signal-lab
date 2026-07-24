@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."
echo ============================================================
echo M10B GOLD Multi-Timeframe Payoff Fresh Shadow - ONE SHOT
echo ============================================================
python "scripts\mochipoyo_alert_research\m10b\python\m10b_runtime.py" once
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10B one-shot was blocked. Do not reset anything.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)
echo.
echo [DONE] M10B one-shot PASS. NEXT: run 03_run_shadow_forever.bat.
pause
exit /b 0
