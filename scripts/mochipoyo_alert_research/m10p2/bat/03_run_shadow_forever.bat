@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10P2 C0212 Fresh Prospective Shadow - FOREVER
echo BOUNDED CSV VERIFIED JOURNAL V2 - PRESERVED START - AUDIT ONLY
echo ============================================================
echo.
echo Requires reviewed bounded CSV adapter migration PASS.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P running unchanged.
echo Transient MT5 CSV rebuild/read contention waits and retries.
echo Journal SHA256 plus genuine runtime/start/timestamp/overlap failures stop fail-closed.
echo Do NOT rerun BAT01.
echo.

python "scripts\mochipoyo_alert_research\common\python\run_bounded_adapter_loop_v2.py" --loop M10P2 --interval-seconds 60 --compat-process-marker m10p2_guarded_runtime.py
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10P2 loop was BLOCKED. Do NOT reset/reinitialize anything.
  echo Send the complete console output and latest M10P2 status/log to ChatGPT.
  pause
  exit /b %RC%
)

echo [DONE] M10P2 loop stopped gracefully. Runtime manifest and frozen start were preserved.
pause
exit /b 0
