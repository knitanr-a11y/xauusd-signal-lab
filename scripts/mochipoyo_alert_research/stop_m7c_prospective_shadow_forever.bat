@echo off
setlocal EnableExtensions DisableDelayedExpansion

if defined LOCALAPPDATA (
  set "LOCAL_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"
) else (
  set "LOCAL_ROOT=%TEMP%\xauusd_signal_lab\mochipoyo_alert_research"
)
set "STOP_FILE=%LOCAL_ROOT%\STOP_M7C_SHADOW_LOOP"

if not exist "%LOCAL_ROOT%" (
  mkdir "%LOCAL_ROOT%" >nul 2>&1
)
> "%STOP_FILE%" echo stop requested

echo [OK] M7C shadow stop request created:
echo %STOP_FILE%
echo The running M7C loop will stop safely after the current cycle or wait interval.
echo.
pause
exit /b 0
