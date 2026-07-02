@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "LOG=%CD%\BTCUSD_H4_WARMUP_LAST_LOG.txt"
set "SUMMARY=%CD%\BTCUSD_H4_WARMUP_PASTE_THIS.txt"
set "PACKAGE=%CD%\BTCUSD_H4_WARMUP_PACKAGE.zip"

if exist "%SUMMARY%" del /q "%SUMMARY%" >nul 2>&1
if exist "%PACKAGE%" del /q "%PACKAGE%" >nul 2>&1
if not exist "Files" mkdir "Files"

> "%LOG%" echo BTCUSD# H4 warm-up export
>> "%LOG%" echo Started: %DATE% %TIME%
>> "%LOG%" echo Repository: %CD%
>> "%LOG%" echo H4 only, from 2017-01-01, closed bars only

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
  echo Paste BTCUSD_H4_WARMUP_LAST_LOG.txt into the chat.
  pause
  exit /b 1
)

>> "%LOG%" echo Python command: %PYTHON_CMD%
%PYTHON_CMD% --version >> "%LOG%" 2>&1

echo.
echo BTCUSD# H4 warm-up export is starting.
echo Only H4 from 2017-01-01 will be downloaded.
echo This is much smaller than the full history package.
echo.

%PYTHON_CMD% scripts\btc_ml_v1\data_history\build_btcusd_h4_warmup_package.py %* >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  >> "%LOG%" echo Exit code: %RC%
  echo.
  echo ===== ERROR LOG =====
  type "%LOG%"
  echo =====================
  echo.
  echo Paste BTCUSD_H4_WARMUP_LAST_LOG.txt into the chat.
  pause
  exit /b %RC%
)

if not exist "%PACKAGE%" (
  >> "%LOG%" echo ERROR: H4 warm-up ZIP was not created.
  type "%LOG%"
  echo.
  echo Paste BTCUSD_H4_WARMUP_LAST_LOG.txt into the chat.
  pause
  exit /b 2
)

if not exist "%SUMMARY%" (
  >> "%LOG%" echo ERROR: H4 warm-up summary was not created.
  type "%LOG%"
  echo.
  echo Paste BTCUSD_H4_WARMUP_LAST_LOG.txt into the chat.
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
echo BTCUSD_H4_WARMUP_PACKAGE.zip
echo.
pause
exit /b 0
