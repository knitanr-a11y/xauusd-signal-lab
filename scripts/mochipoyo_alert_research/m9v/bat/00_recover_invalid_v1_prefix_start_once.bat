@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\.."

echo ============================================================
echo M9V v1 Prefix Incident Recovery - ONE TIME ONLY
echo ============================================================
echo.
echo Keep M8C / M7C / genuine source collector RUNNING unchanged.
echo Do NOT run the M9V forever loop during recovery.
echo.
echo This BAT is ONLY for the known v1 incident where 02 blocked with:
echo   historical prefix changed after M9V start: M5
echo.
echo It archives the invalid v1 runtime and receipt first.
echo It refuses recovery if a successful M9V prospective output already exists for that old start.
echo It does NOT create a new M9V start.
echo.

python "scripts\mochipoyo_alert_research\m9v\python\recover_m9v_v1_prefix_incident_once.py"
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo [STOP] M9V recovery was blocked.
  echo Nothing was deleted or replaced.
  echo M8C, M7C, and collector remain unchanged.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo [DONE] Invalid M9V v1 start was archived safely.
echo NEXT: run 01_initialize_fresh_runtime_once.bat exactly once.
pause
exit /b 0
