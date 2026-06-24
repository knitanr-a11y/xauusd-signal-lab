@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "SCRIPT=%~dp0archive_legacy_gold_local_v2.ps1"
if not exist "%SCRIPT%" (
  echo [ERROR] PowerShell script not found:
  echo %SCRIPT%
  pause
  exit /b 1
)

where pwsh.exe >nul 2>nul
if %errorlevel%==0 (
  pwsh.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
) else (
  powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
)

set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [ERROR] Archive tool exited with code %RC%.
) else (
  echo Archive tool finished.
)
pause
exit /b %RC%
