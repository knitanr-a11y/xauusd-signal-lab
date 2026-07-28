@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10P C056 + G013 Fresh Prospective Shadow - FOREVER
echo BOUNDED CSV VERIFIED JOURNAL - PRESERVED START - AUDIT ONLY
echo ============================================================
echo.
echo Requires reviewed bounded CSV adapter migration PASS.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E running unchanged.
echo Transient MT5 CSV rebuild/read contention waits and retries.
echo Genuine runtime/start/timestamp/overlap integrity failures stop fail-closed.
echo Do NOT rerun BAT01.
echo.

python "scripts\mochipoyo_alert_research\common\python\run_bounded_adapter_loop.py" --loop M10P --interval-seconds 60 --compat-process-marker m10p_guarded_runtime.py
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10P loop was BLOCKED. Do NOT reset/reinitialize anything.
  echo Send the complete console output and latest M10P status/log to ChatGPT.
  pause
  exit /b %RC%
)

echo [DONE] M10P loop stopped gracefully. Runtime manifest and frozen start were preserved.
pause
exit /b 0
