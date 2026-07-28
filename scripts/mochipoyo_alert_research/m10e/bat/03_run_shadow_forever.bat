@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10E H1 Baseline vs Compound-Filter Shadow - FOREVER
echo BOUNDED CSV VERIFIED JOURNAL - PRESERVED START - AUDIT ONLY
echo ============================================================
echo.
echo Requires reviewed bounded CSV adapter migration PASS.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B running unchanged.
echo Transient MT5 CSV rebuild/read contention waits and retries.
echo Genuine runtime/start/timestamp/overlap integrity failures stop fail-closed.
echo Do NOT rerun BAT01.
echo.

python "scripts\mochipoyo_alert_research\common\python\run_bounded_adapter_loop.py" --loop M10E --interval-seconds 60 --compat-process-marker m10e_runtime.py
set "RC=%ERRORLEVEL%"
echo.
echo M10E loop exited with code %RC%.
if not "%RC%"=="0" echo Send the full screen output and latest M10E status/log to ChatGPT. Do NOT reinitialize.
echo Runtime manifest and frozen start remain unchanged.
pause
exit /b %RC%
