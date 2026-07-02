@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "LOG=%CD%\BTCUSD_HISTORY_LAST_LOG.txt"
set "SUMMARY=%CD%\BTCUSD_HISTORY_PASTE_THIS.txt"
set "PACKAGE=%CD%\BTCUSD_HISTORY_CHAT_PACKAGE.zip"

if exist "%SUMMARY%" del /q "%SUMMARY%" >nul 2>&1
if exist "%PACKAGE%" del /q "%PACKAGE%" >nul 2>&1
if not exist "Files" mkdir "Files"

> "%LOG%" echo BTCUSD# compressed chat package export
>> "%LOG%" echo Started: %DATE% %TIME%
>> "%LOG%" echo Repository: %CD%
>> "%LOG%" echo M1=90 days, M5=730 days, M15/H1/H4/D1=730 days
>> "%LOG%" echo Output=standard ZIP DEFLATE level 9, no password

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
echo BTCUSD# compressed package is starting.
echo M1: latest 90 days
echo M5: latest 730 days
echo M15 H1 H4 D1: latest 730 days
echo The temporary CSV files will be deleted after ZIP creation.
echo.

%PYTHON_CMD% scripts\btc_ml_v1\data_history\build_btcusd_chat_package.py %* >> "%LOG%" 2>&1
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

if not exist "%PACKAGE%" (
  >> "%LOG%" echo ERROR: ZIP package was not created.
  type "%LOG%"
  echo.
  echo Paste BTCUSD_HISTORY_LAST_LOG.txt into the chat.
  pause
  exit /b 2
)

if not exist "%SUMMARY%" (
  >> "%LOG%" echo ERROR: Summary file was not created.
  type "%LOG%"
  echo.
  echo Paste BTCUSD_HISTORY_LAST_LOG.txt into the chat.
  pause
  exit /b 3
)

>> "%LOG%" echo Completed successfully: %DATE% %TIME%

echo.
echo ===== SUCCESS =====
type "%SUMMARY%"
echo ===================
echo.
echo Upload this file to the chat:
echo BTCUSD_HISTORY_CHAT_PACKAGE.zip
echo.
echo Full execution log: BTCUSD_HISTORY_LAST_LOG.txt
echo.
pause
exit /b 0
