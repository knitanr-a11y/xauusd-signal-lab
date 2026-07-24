@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M10I Mochipoyo-Independent M15 SHORT Archetype Discovery
echo HISTORICAL AUDIT ONLY - DO NOT TOUCH FORWARD MONITORS
echo ============================================================
echo.
echo Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E running unchanged.
echo This stage does NOT use KERNEL-S1, M10F C0049, or M10G entries as its candidate universe.
echo.

set "M10I_PYDIR=scripts\mochipoyo_alert_research\m10i\python"
set "M10I_MAIN=%M10I_PYDIR%\run_independent_m15_short_archetype_discovery.py"

if not exist "%M10I_MAIN%" (
  echo [M10I BLOCKED] Required main script is missing: %M10I_MAIN%
  echo [SAFE] Do not modify thresholds, hashes, forward starts, or running monitors.
  echo [ACTION] Send the complete console output to ChatGPT.
  pause
  exit /b 2
)

python -c "import sys,bisect; sys.path.insert(0,r'%M10I_PYDIR%'); import run_independent_m15_short_archetype_discovery as impl; cache={}; exec('def cached(bars, delta, decision):\n    key=(id(bars), delta.total_seconds())\n    times=cache.get(key)\n    if times is None:\n        times=[bar.time+delta for bar in bars]\n        cache[key]=times\n    return bisect.bisect_right(times, decision)-1'); impl.selected_closed_index=cached; raise SystemExit(impl.main())"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M10I was BLOCKED. Do not modify thresholds, hashes, forward starts, or running monitors.
  echo Send the complete console output to ChatGPT.
  pause
  exit /b %RC%
)
echo [M10I PASS] Historical independent SHORT discovery completed.
echo Run 02_open_latest_results.bat and upload only 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
