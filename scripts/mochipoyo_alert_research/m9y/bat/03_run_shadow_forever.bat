@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M9Y GOLD Payoff Fresh Prospective Shadow - PERSISTENT
echo BOUNDED CSV VERIFIED JOURNAL - PRESERVED START - AUDIT ONLY
echo ============================================================
echo Keep this window OPEN. Keep M8C / M7C / collector / M9V running in parallel.
echo Requires reviewed bounded CSV adapter migration PASS.
echo Audit-only: Discord OFF / MT5 orders OFF / live gate OFF.
echo Transient MT5 CSV rebuild/read contention waits and retries.
echo Genuine runtime/start/timestamp/overlap integrity failures stop fail-closed.
echo Stop safely with 04_stop_shadow_forever.bat.
echo Do NOT rerun BAT01.
echo.

python "scripts\mochipoyo_alert_research\common\python\run_bounded_adapter_loop.py" --loop M9Y --interval-seconds 60 --compat-process-marker run_m9y_shadow_forever_safe.py
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [M9Y LOOP STOPPED] normal stop.
) else (
  echo [M9Y LOOP BLOCKED] exit code %RC%. Send full output and latest M9Y log/status to ChatGPT. Do NOT reinitialize.
)
echo Existing M8C/M7C/M9V, runtime manifest, and frozen start remain unchanged.
pause
exit /b %RC%
