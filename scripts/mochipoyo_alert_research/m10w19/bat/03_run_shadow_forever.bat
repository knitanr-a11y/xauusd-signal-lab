@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10W19 BLC1 ATR Filter Fresh Shadow - FOREVER
echo BOUNDED CSV VERIFIED JOURNAL - PRESERVED START - AUDIT ONLY
echo ============================================================
echo.
echo Requires reviewed bounded CSV adapter migration PASS.
echo Keep collector / M7C / M8C and all upstream fresh loops running unchanged.
echo Transient MT5 CSV rebuild/read contention waits and retries.
echo Genuine runtime/start/timestamp/overlap integrity failures stop fail-closed.
echo No Discord send. No MT5 orders. No existing monitor reset.
echo Do NOT rerun BAT01.
echo.

python "scripts\mochipoyo_alert_research\common\python\run_bounded_adapter_loop.py" --loop M10W19 --interval-seconds 60 --compat-process-marker m10w19_runtime.py
set "RC=%ERRORLEVEL%"
echo.
echo [M10W19 EXIT] code=%RC%
if not "%RC%"=="0" echo Send the full screen output and latest M10W19 status/log to ChatGPT. Do NOT reinitialize.
echo Runtime manifest and frozen start remain unchanged.
pause
exit /b %RC%
