@echo off
setlocal
set STATE=%LOCALAPPDATA%\xauusd_signal_lab\btc_stage55_shadow\runtime_health.json
if not exist "%STATE%" (
  echo runtime_health.json not found: %STATE%
  pause
  exit /b 1
)
type "%STATE%"
echo.
pause
