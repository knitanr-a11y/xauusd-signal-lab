@echo off
setlocal
title BTC Stage55 Shadow - Runtime Status
echo ============================================================
echo BTC STAGE55 SHADOW - RUNTIME STATUS
echo ============================================================
set STATE=%LOCALAPPDATA%\xauusd_signal_lab\btc_stage55_shadow\runtime_health.json
if not exist "%STATE%" (
  echo [BTC_STAGE55_SHADOW] runtime_health.json not found:
  echo %STATE%
  pause
  exit /b 1
)
type "%STATE%"
echo.
pause
