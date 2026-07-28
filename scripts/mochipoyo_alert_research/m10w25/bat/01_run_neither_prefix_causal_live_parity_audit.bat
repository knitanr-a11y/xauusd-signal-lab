@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W25 NEITHER Prefix-Causal Live Parity Audit - READ ONLY
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 / M10W19 running unchanged.
echo M10W19 BAT03 continues unchanged. NEVER rerun M10W19 BAT01.
echo This audit reads frozen bars, M10W14 coverage grid, and M10W24B PRE-ENTRY feature rows only.
echo It does NOT read trade outcomes, PF/PnL, future returns, or future path labels.
echo It does NOT create a prospective start.
echo.

python "scripts\mochipoyo_alert_research\m10w25\python\run_m10w25_neither_prefix_causal_live_parity_audit.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10W25 was BLOCKED. Do not force a pass, change thresholds, or reset anything.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W25\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [M10W25 COMPLETE]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened M10W25 LATEST folder.
pause
exit /b 0
