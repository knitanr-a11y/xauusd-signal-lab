@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

if defined LOCALAPPDATA (
  set "LOCAL_ROOT=%LOCALAPPDATA%\xauusd_signal_lab"
) else (
  set "LOCAL_ROOT=%TEMP%\xauusd_signal_lab"
)

set "SOURCE_DB=%LOCAL_ROOT%\mochipoyo_alert_research\mochipoyo_alerts.sqlite3"
set "OUTPUT_ROOT=%LOCAL_ROOT%\btc_ml_v1\outputs\BCR01_outcome_blind_source_snapshot"
set "LATEST_ZIP=%OUTPUT_ROOT%\LATEST\99_UPLOAD_PACKAGE.zip"
set "SCRIPT=scripts\btc_ml_v1\BCR01_outcome_blind_source_snapshot\python\run_bcr01_outcome_blind_source_snapshot.py"

set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  echo [BCR01] FAILED: Python was not found.
  pause
  exit /b 9009
)

if not exist "%SOURCE_DB%" (
  echo [BCR01] FAILED: Source database was not found.
  echo %SOURCE_DB%
  echo Collector and M7C were not changed.
  pause
  exit /b 2
)

if not exist "%SCRIPT%" (
  echo [BCR01] FAILED: Snapshot script was not found.
  echo %SCRIPT%
  pause
  exit /b 2
)

echo ============================================================
echo BCR01 - OUTCOME-BLIND COLLECTOR SOURCE SNAPSHOT
echo ============================================================
echo Source DB      : %SOURCE_DB%
echo Output root    : %OUTPUT_ROOT%
echo Source mode    : READ-ONLY SQLite transaction
echo Collector/M7C  : KEEP RUNNING, NO CHANGE
echo Outcome tables : NOT QUERIED OR EXPORTED
echo Candidate eval : NOT PERFORMED
echo Discord/MT5    : OFF
echo ============================================================
echo.

%PYTHON_CMD% "%SCRIPT%" --source-db "%SOURCE_DB%" --output-root "%OUTPUT_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"

if exist "%LATEST_ZIP%" (
  start "" explorer.exe /select,"%LATEST_ZIP%"
) else if exist "%OUTPUT_ROOT%\LATEST" (
  start "" explorer.exe "%OUTPUT_ROOT%\LATEST"
)

echo.
echo [BCR01] exit_code=%EXIT_CODE%
if "%EXIT_CODE%"=="0" (
  echo [BCR01] Snapshot completed. Upload the selected ZIP and stop.
) else (
  echo [BCR01] Snapshot blocked or failed. Upload the error ZIP if one was created and stop.
)
pause
exit /b %EXIT_CODE%
