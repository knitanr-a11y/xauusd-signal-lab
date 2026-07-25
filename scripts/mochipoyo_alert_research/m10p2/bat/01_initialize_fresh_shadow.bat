@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10P2 C0212 Fresh Prospective Shadow - INITIALIZE ONCE
echo AUDIT ONLY - THIS BAT MUST NEVER BE RERUN AFTER INIT PASS
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P running unchanged.
echo This freezes a BRAND-NEW C0212 MT5-server start. It does NOT reuse M10P start.
echo No historical backfill. No Discord. No MT5 orders.
echo.

python "scripts\mochipoyo_alert_research\m10p2\python\m10p2_runtime.py" initialize
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10P2 initialization was BLOCKED.
  echo Do NOT delete runtime files, change C0212 thresholds, or reset any running monitor.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)

echo [M10P2 INIT PASS]
echo NEVER run this BAT again.
echo Next run 02_run_bootstrap_once_and_open_results.bat.
pause
exit /b 0
