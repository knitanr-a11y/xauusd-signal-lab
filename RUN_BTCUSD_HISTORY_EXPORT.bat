@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "LOG=%CD%\BTCUSD_HISTORY_LAST_LOG.txt"
set "SUMMARY=%CD%\BTCUSD_HISTORY_PASTE_THIS.txt"

if exist "%SUMMARY%" del /q "%SUMMARY%" >nul 2>&1
if not exist "Files" mkdir "Files"

set "START_DATE="
for /f %%I in ('powershell -NoProfile -Command "(Get-Date).ToUniversalTime().AddDays(-730).ToString('yyyy-MM-dd')"') do set "START_DATE=%%I"

> "%LOG%" echo BTCUSD# lightweight history export
>> "%LOG%" echo Started: %DATE% %TIME%
>> "%LOG%" echo Repository: %CD%
>> "%LOG%" echo Default mode: last 730 days, M15 H1 H4 D1 only

if not defined START_DATE (
  >> "%LOG%" echo ERROR: PowerShell could not calculate the UTC start date.
  type "%LOG%"
  echo.
  echo Paste BTCUSD_HISTORY_LAST_LOG.txt into the chat.
  pause
  exit /b 1
)

>> "%LOG%" echo Start date UTC: %START_DATE%

set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  >> "%LOG%" echo ERROR: Python was not found. Install Python or add it to PATH.
  type "%LOG%"
  echo.
  echo Paste BTCUSD_HISTORY_LAST_LOG.txt into the chat.
  pause
  exit /b 1
)

>> "%LOG%" echo Python command: %PYTHON_CMD%
%PYTHON_CMD% --version >> "%LOG%" 2>&1

echo.
echo BTCUSD# lightweight export is starting.
echo Only M15, H1, H4 and D1 for the latest 730 days will be downloaded.
echo M1 and M5 are intentionally excluded to keep the data small.
echo.

%PYTHON_CMD% scripts\btc_ml_v1\data_history\run_btcusdsharp_history.py --start "%START_DATE%" --timeframes M15 H1 H4 D1 %* >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  >> "%LOG%" echo Exit code: %RC%
  echo.
  echo ===== ERROR LOG =====
  type "%LOG%"
  echo =====================
  echo.
  echo Paste BTCUSD_HISTORY_LAST_LOG.txt into the chat.
  pause
  exit /b %RC%
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='Files\btcusdsharp_backups'; if(Test-Path -LiteralPath $p){Get-ChildItem -LiteralPath $p -Directory | Sort-Object LastWriteTime -Descending | Select-Object -Skip 1 | Remove-Item -Recurse -Force}" >> "%LOG%" 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command "$m=Get-Content -Raw -LiteralPath 'Files\btcusdsharp_history_manifest.json' | ConvertFrom-Json; $o=@(); $o+='BTCUSD# LIGHTWEIGHT HISTORY RESULT'; $o+=('generated_at_utc: '+$m.generated_at_utc); $o+=('symbol: '+$m.symbol); $o+=('requested_start_utc: '+$m.requested_start_utc); $o+=('snapshot_end_utc: '+$m.snapshot_end_utc); $o+='mode: latest 730 days / M15 H1 H4 D1 / closed bars only'; foreach($t in $m.timeframes){$o+=('{0}: rows={1}, first={2}, last={3}, gaps={4}, max_gap_seconds={5}' -f $t.timeframe,$t.rows,$t.first_time_utc,$t.last_time_utc,$t.gaps_over_one_bar,$t.maximum_gap_seconds)}; if($m.warnings.Count -gt 0){$o+='WARNINGS:'; foreach($w in $m.warnings){$o+=('- '+$w)}}; $o | Set-Content -Encoding UTF8 -LiteralPath 'BTCUSD_HISTORY_PASTE_THIS.txt'" >> "%LOG%" 2>&1

if not exist "%SUMMARY%" (
  >> "%LOG%" echo ERROR: Export succeeded but the paste summary could not be created.
  echo.
  type "%LOG%"
  echo.
  echo Paste BTCUSD_HISTORY_LAST_LOG.txt into the chat.
  pause
  exit /b 2
)

>> "%LOG%" echo Completed successfully: %DATE% %TIME%

echo.
echo ===== SUCCESS =====
type "%SUMMARY%"
echo ===================
echo.
echo Paste BTCUSD_HISTORY_PASTE_THIS.txt into the chat.
echo Full execution log: BTCUSD_HISTORY_LAST_LOG.txt
echo Data folder: Files
echo.
pause
exit /b 0
