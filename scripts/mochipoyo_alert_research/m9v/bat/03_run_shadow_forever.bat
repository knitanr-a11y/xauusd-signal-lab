@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M9V GOLD Multi-Timeframe Prospective Shadow - PERSISTENT
echo BOUNDED CSV VERIFIED JOURNAL V3 - IMMUTABLE START BOOTSTRAP
echo ============================================================
echo.
echo Keep this window OPEN.
echo Keep M8C / M7C / genuine source collector RUNNING in parallel.
echo Requires reviewed bounded CSV adapter migration PASS.
echo M9V is audit-only: Discord OFF / MT5 orders OFF / live gate OFF.
echo The frozen runtime state-at-start is the authoritative bootstrap.
echo Old bounded-source head rows are NOT reconstructed or backfilled.
echo Transient MT5 CSV rebuild/read contention waits and retries.
echo Journal SHA256 plus genuine runtime/start/timestamp/overlap failures stop fail-closed.
echo Stop safely with 04_stop_shadow_forever.bat.
echo Do NOT rerun BAT00/BAT01.
echo.

python "scripts\mochipoyo_alert_research\common\python\run_bounded_adapter_loop_v3.py" --loop M9V --interval-seconds 60 --compat-process-marker run_m9v_shadow_forever_safe
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo [M9V LOOP STOPPED] normal stop request or manual close.
) else (
  echo [M9V LOOP BLOCKED] exit code %RC%.
  echo Do not reset/reinitialize M9V. Send the full screen output and latest M9V log/status to ChatGPT.
)
echo M8C, M7C, collector, runtime manifest, and frozen start remain unchanged.
pause
exit /b %RC%
