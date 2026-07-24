@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M9V GOLD Multi-Timeframe Prospective Shadow v2 - PERSISTENT
echo ============================================================
echo.
echo Keep this window OPEN.
echo Keep M8C / M7C / genuine source collector RUNNING in parallel.
echo M9V is audit-only: Discord OFF / MT5 orders OFF / live gate OFF.
echo The loop runs every 60 seconds and stops fail-closed on contract/data-integrity error.
echo Stop safely with 04_stop_shadow_forever.bat.
echo.

python "scripts\mochipoyo_alert_research\m9v\python\run_m9v_shadow_forever_safe_v2.py" --interval-seconds 60
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo [M9V LOOP STOPPED] normal stop request or manual close.
) else (
  echo [M9V LOOP BLOCKED] exit code %RC%.
  echo Do not reset M9V. Send the full screen output and latest M9V log/status to ChatGPT.
)
echo M8C, M7C, and collector are separate and remain unchanged.
pause
exit /b %RC%
