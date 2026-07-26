@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10Q DUAL SHORT FRESH CHECKPOINT AUDIT
echo READ-ONLY / AUDIT-ONLY
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 running unchanged.
echo This reads M10P and M10P2 LATEST only. It does not reset starts, runtimes, thresholds, or ledgers.
echo.

python "scripts\mochipoyo_alert_research\m10q\python\run_m10q_dual_fresh_checkpoint_audit.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10Q checkpoint audit was BLOCKED.
  echo Do NOT reset or reinitialize any forward monitor. Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10Q\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10Q PASS]
echo Upload only 99_UPLOAD_PACKAGE.zip when you want a fresh checkpoint review.
echo This BAT is read-only with respect to M10P/M10P2 and is safe to rerun.
pause
exit /b 0
