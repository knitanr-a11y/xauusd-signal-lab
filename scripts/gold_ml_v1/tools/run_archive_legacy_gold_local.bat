@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "SCRIPT=%~dp0archive_legacy_gold_local_v2.ps1"
set "VALIDATOR=%~dp0validate_archive_tool.ps1"

if not exist "%SCRIPT%" (
  echo [ERROR] PowerShell script not found:
  echo %SCRIPT%
  pause
  exit /b 1
)
if not exist "%VALIDATOR%" (
  echo [ERROR] Validator script not found:
  echo %VALIDATOR%
  pause
  exit /b 1
)

where pwsh.exe >nul 2>nul
if %errorlevel%==0 (
  set "PSEXE=pwsh.exe"
) else (
  set "PSEXE=powershell.exe"
)

"%PSEXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%VALIDATOR%" -ScriptPath "%SCRIPT%"
if not "%ERRORLEVEL%"=="0" (
  echo.
  echo [ERROR] PowerShell syntax validation failed. Nothing was archived.
  pause
  exit /b 1
)

"%PSEXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo [ERROR] Archive tool exited with code %RC%.
) else (
  echo Archive tool finished.
)
pause
exit /b %RC%
