@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W12 Dual SHORT Threshold Activation-Distance Audit
echo READ ONLY - GOLD / XAUUSD ONLY
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 running unchanged.
echo Do NOT run M10P BAT01 or M10P2 BAT01.
echo Do NOT change any threshold or prospective start.
echo Near-miss output is descriptive only and must NOT be used to refit thresholds.
echo.

python "scripts\mochipoyo_alert_research\m10w12\python\run_m10w12_dual_short_threshold_activation_distance_audit.py"
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo [STOP] M10W12 was BLOCKED.
  echo Do NOT change thresholds/starts or reset runtimes to force a pass.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W12\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W12 PASS]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W12 LATEST folder.
pause
exit /b 0
