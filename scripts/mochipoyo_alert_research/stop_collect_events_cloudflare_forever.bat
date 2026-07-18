@echo off
setlocal EnableExtensions DisableDelayedExpansion

if defined LOCALAPPDATA (
  set "LOCAL_ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"
) else (
  set "LOCAL_ROOT=%TEMP%\xauusd_signal_lab\mochipoyo_alert_research"
)
set "STOP_FILE=%LOCAL_ROOT%\STOP_COLLECTOR_LOOP"

if not exist "%LOCAL_ROOT%" mkdir "%LOCAL_ROOT%" >nul 2>&1

>"%STOP_FILE%" echo requested_at=%DATE% %TIME%

echo ============================================================
echo Mochipoyo collector stop requested
echo Stop file: %STOP_FILE%
echo ============================================================
echo The collector checks this file at least once per second while waiting.
echo If a Cloudflare request is currently running, shutdown may take up to
 echo the request timeout to complete.
echo Discord send: OFF
 echo MT5 orders  : OFF
 echo.
pause
exit /b 0
