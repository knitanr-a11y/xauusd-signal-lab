@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10B GOLD Multi-Timeframe Payoff Fresh Shadow - FOREVER
echo BOUNDED CSV VERIFIED JOURNAL V2 - PRESERVED START - AUDIT ONLY
echo ============================================================
echo Keep collector / M7C / M8C / M9V / M9Y running unchanged.
echo Requires reviewed bounded CSV adapter migration PASS.
echo Transient MT5 CSV rebuild/read contention waits and retries.
echo Journal SHA256 plus genuine runtime/start/timestamp/overlap failures stop fail-closed.
echo Do not close this window during normal monitoring.
echo Do NOT rerun BAT01.
echo.

python "scripts\mochipoyo_alert_research\common\python\run_bounded_adapter_loop_v2.py" --loop M10B --interval-seconds 60 --compat-process-marker m10b_runtime.py
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [STOP] M10B loop was blocked. Do not reset/reinitialize anything.
  echo Send the full screen output and latest M10B status/log to ChatGPT.
  pause
  exit /b %RC%
)
echo.
echo [DONE] M10B loop stopped gracefully. Runtime manifest and frozen start were preserved.
pause
exit /b 0
