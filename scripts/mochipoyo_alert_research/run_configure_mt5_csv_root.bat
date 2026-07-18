@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "SCRIPT_DIR=%~dp0"
echo ============================================================
echo Mochipoyo MT5 CSV root configuration
 echo CSV write    : OFF
 echo Database write: OFF
 echo Discord send : OFF
 echo MT5 orders   : OFF
 echo ============================================================
echo.
py -3.12 "%SCRIPT_DIR%configure_mt5_csv_root.py"
set "EXITCODE=%ERRORLEVEL%"
echo.
pause
exit /b %EXITCODE%
