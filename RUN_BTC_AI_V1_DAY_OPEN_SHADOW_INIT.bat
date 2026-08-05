@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "LOG=%CD%\BTC_AI_V1_DAY_OPEN_SHADOW_INIT_LAST_LOG.txt"
set "INSTALLER=%CD%\scripts\btc_ai_v1\install_shadow_day_open_matched_pair_v1.py"
set "RUNTIME=%CD%\scripts\btc_ai_v1\shadow_day_open_matched_pair_v1.py"

set "M1=%~1"
set "M15=%~2"
set "H4=%~3"
set "D1=%~4"
if not defined M1 set "M1=%CD%\data\mt5\btcusd_m1_latest.csv"
if not defined M15 set "M15=%CD%\data\mt5\btcusd_m15_latest.csv"
if not defined H4 set "H4=%CD%\data\mt5\btcusd_h4_latest.csv"
if not defined D1 set "D1=%CD%\data\mt5\btcusd_d1_latest.csv"

> "%LOG%" echo BTC AI V1 Day Open Matched-Pair Shadow V1 one-time initialization
>> "%LOG%" echo Started: %DATE% %TIME%
>> "%LOG%" echo Repository: %CD%
>> "%LOG%" echo M1: %M1%
>> "%LOG%" echo M15: %M15%
>> "%LOG%" echo H4: %H4%
>> "%LOG%" echo D1: %D1%

set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  >> "%LOG%" echo ERROR: Python was not found. Install Python or add it to PATH.
  goto :fail_1
)

>> "%LOG%" echo Python command: %PYTHON_CMD%
%PYTHON_CMD% --version >> "%LOG%" 2>&1

if not exist "%INSTALLER%" (
  >> "%LOG%" echo ERROR: Installer was not found: %INSTALLER%
  goto :fail_2
)
if not exist "%M1%" (
  >> "%LOG%" echo ERROR: M1 CSV was not found: %M1%
  goto :fail_3
)
if not exist "%M15%" (
  >> "%LOG%" echo ERROR: M15 CSV was not found: %M15%
  goto :fail_3
)
if not exist "%H4%" (
  >> "%LOG%" echo ERROR: H4 CSV was not found: %H4%
  goto :fail_3
)
if not exist "%D1%" (
  >> "%LOG%" echo ERROR: D1 CSV was not found: %D1%
  goto :fail_3
)

echo.
echo Installing and verifying the frozen Shadow V1 package...
%PYTHON_CMD% "%INSTALLER%" >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" goto :runtime_fail

if not exist "%RUNTIME%" (
  >> "%LOG%" echo ERROR: Runtime was not installed: %RUNTIME%
  goto :fail_4
)

echo Creating the Fresh no-backfill activation watermark...
%PYTHON_CMD% "%RUNTIME%" init --m1 "%M1%" --m15 "%M15%" --h4 "%H4%" --d1 "%D1%" >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" goto :runtime_fail

>> "%LOG%" echo Completed successfully: %DATE% %TIME%
echo.
echo ===== SUCCESS =====
echo Shadow V1 was initialized once with a Fresh no-backfill watermark.
echo Do not run this INIT BAT again.
echo Use RUN_BTC_AI_V1_DAY_OPEN_SHADOW.bat after each CSV refresh.
echo Full log: BTC_AI_V1_DAY_OPEN_SHADOW_INIT_LAST_LOG.txt
echo ===================
echo.
pause
exit /b 0

:runtime_fail
>> "%LOG%" echo Exit code: %RC%
echo.
echo ===== ERROR LOG =====
type "%LOG%"
echo =====================
echo.
echo Initialization did not complete. Do not delete or edit runtime state by hand.
echo Paste BTC_AI_V1_DAY_OPEN_SHADOW_INIT_LAST_LOG.txt into the chat.
pause
exit /b %RC%

:fail_1
set "RC=1"
goto :runtime_fail
:fail_2
set "RC=2"
goto :runtime_fail
:fail_3
set "RC=3"
goto :runtime_fail
:fail_4
set "RC=4"
goto :runtime_fail
