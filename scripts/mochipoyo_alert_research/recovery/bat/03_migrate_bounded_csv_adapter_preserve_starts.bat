@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\..\.."

echo ============================================================
echo MOCHIPOYO - BOUNDED CSV ADAPTER ONE-TIME MIGRATION V2
echo PRESERVE ALL FROZEN STARTS - VERIFIED JOURNALS - AUDIT ONLY
echo ============================================================
echo.
echo This reads the current bounded MT5 CSVs and creates verified local journals.
echo It verifies every journal SHA256 before and after any adapter update.
echo It does NOT run BAT01, restart loops, edit runtime manifests,
echo reset prospective starts, backfill pre-start candidates, send Discord,
echo or place MT5 orders.
echo.
echo Required: M9V M9Y M10B M10E M10P M10P2 M10W19 must all be stopped.
echo.

python "scripts\mochipoyo_alert_research\recovery\python\migrate_bounded_csv_source_adapter_v2.py"
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo [STOP] Bounded CSV adapter migration was BLOCKED.
  echo Do not delete adapter/runtime/lock files manually and do not run BAT01.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

set "LATEST=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\BOUNDED_CSV_SOURCE_ADAPTER_MIGRATION\LATEST"
if exist "%LATEST%" start "" explorer "%LATEST%"
echo.
echo [MIGRATION COMPLETE - REVIEW REQUIRED]
echo Upload only 99_UPLOAD_PACKAGE.zip from the opened LATEST folder.
echo Do NOT run any BAT03 until ChatGPT reviews the migration package.
pause
exit /b 0
