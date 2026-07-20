@echo off
setlocal EnableExtensions DisableDelayedExpansion

if defined LOCALAPPDATA (
  set "LOCAL_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"
) else (
  set "LOCAL_ROOT=%TEMP%\xauusd_signal_lab\mochipoyo_alert_research"
)
set "COLLECTOR_DIR=%LOCAL_ROOT%\logs\collector"
set "M7C_DIR=%LOCAL_ROOT%\logs\m7c"
set "DERIVED_DIR=%LOCAL_ROOT%\logs\derived"

if not exist "%COLLECTOR_DIR%" mkdir "%COLLECTOR_DIR%"
if not exist "%M7C_DIR%" mkdir "%M7C_DIR%"
if not exist "%DERIVED_DIR%" mkdir "%DERIVED_DIR%"

start "Mochipoyo Collector Logs" explorer.exe "%COLLECTOR_DIR%"
start "Mochipoyo M7C Logs" explorer.exe "%M7C_DIR%"
start "Mochipoyo Derived Audit" explorer.exe "%DERIVED_DIR%"

exit /b 0
