@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W14 GOLD Directional Coverage / Blind Spot Map - READ ONLY
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 running unchanged.
echo This stage reads frozen GOLD history for candidate COVERAGE only.
echo It does NOT evaluate trade outcomes, PF, PnL, win rate, or future labels.
echo It does NOT change any threshold, formula, start, runtime, or monitor.
echo.

python "scripts\mochipoyo_alert_research\m10w14\python\run_m10w14_gold_directional_coverage_blind_spot_map.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10W14 was BLOCKED. Do not force a pass or change thresholds.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W14\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W14 COMPLETE]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W14 LATEST folder.
pause
exit /b 0
