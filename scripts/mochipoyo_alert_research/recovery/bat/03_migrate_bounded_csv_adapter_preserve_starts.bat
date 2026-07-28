@echo off
setlocal EnableExtensions DisableDelayedExpansion

for %%I in ("%~dp0\..\..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"
if not exist "config\mochipoyo_alert_research\current_state_20260728.json" (
  echo [STOP] Repository root could not be resolved from this BAT.
  echo BAT:  %~f0
  echo ROOT: %REPO_ROOT%
  echo Do not run BAT01, delete locks, or change any prospective start.
  pause
  exit /b 2
)

set "ADAPTER=scripts\mochipoyo_alert_research\common\python\bounded_csv_source_adapter.py"
set "INTEGRITY=scripts\mochipoyo_alert_research\common\python\bounded_csv_journal_integrity.py"
set "MIGRATION_CORE=scripts\mochipoyo_alert_research\recovery\python\migrate_bounded_csv_source_adapter.py"
set "MIGRATION_V2=scripts\mochipoyo_alert_research\recovery\python\migrate_bounded_csv_source_adapter_v2.py"

if not exist "%ADAPTER%" goto :missing_files
if not exist "%INTEGRITY%" goto :missing_files
if not exist "%MIGRATION_CORE%" goto :missing_files
if not exist "%MIGRATION_V2%" goto :missing_files

echo ============================================================
echo MOCHIPOYO - BOUNDED CSV ADAPTER ONE-TIME MIGRATION V2
echo PRESERVE ALL FROZEN STARTS - VERIFIED JOURNALS - AUDIT ONLY
echo ============================================================
echo.
echo Repository root: %CD%
echo This reads the current bounded MT5 CSVs and creates verified local journals.
echo It verifies journal fingerprints and uses transactional rollback for updates.
echo It does NOT run BAT01, restart loops, edit runtime manifests,
echo reset prospective starts, backfill pre-start candidates, send Discord,
echo or place MT5 orders.
echo.
echo Required: M9V M9Y M10B M10E M10P M10P2 M10W19 must all be stopped.
echo.

python "%MIGRATION_V2%"
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

:missing_files
echo ============================================================
echo [STOP] REQUIRED MIGRATION FILES ARE MISSING

echo ============================================================
echo Repository root: %CD%
echo.
if not exist "%ADAPTER%" echo MISSING: %ADAPTER%
if not exist "%INTEGRITY%" echo MISSING: %INTEGRITY%
if not exist "%MIGRATION_CORE%" echo MISSING: %MIGRATION_CORE%
if not exist "%MIGRATION_V2%" echo MISSING: %MIGRATION_V2%
echo.
echo Confirm branch feature/mochipoyo-alert-research in GitHub Desktop,
echo then Fetch origin and Pull origin again.
echo Do not delete files manually, run BAT01/BAT03, or change any start.
pause
exit /b 2
