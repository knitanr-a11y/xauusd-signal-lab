@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."
echo ============================================================
echo M10B GOLD Multi-Timeframe Payoff Fresh Shadow - FOREVER
echo ============================================================
echo Keep collector / M7C / M8C / M9V / M9Y running unchanged.
echo Do not close this window during normal monitoring.
echo.
python "scripts\mochipoyo_alert_research\m10b\python\m10b_runtime.py" forever
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10B loop was blocked. Do not reset/reinitialize anything.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)
echo.
echo [DONE] M10B loop stopped gracefully.
pause
exit /b 0
