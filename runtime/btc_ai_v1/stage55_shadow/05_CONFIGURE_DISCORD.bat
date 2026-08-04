@echo off
setlocal
title BTC Stage55 Shadow - Configure Discord
cd /d "%~dp0"
echo ============================================================
echo BTC STAGE55 SHADOW - DISCORD CONFIGURATION
echo Entry notification only / MT5 orders OFF
echo ============================================================
if not exist local_config.json (
  echo [BTC_STAGE55_SHADOW] local_config.json not found. Run 02_BOOTSTRAP_ACTIVATE.bat first.
  pause
  exit /b 1
)
notepad local_config.json
echo.
echo [BTC_STAGE55_SHADOW] Set discord.enabled=true and paste the Webhook URL locally.
echo Do not commit the Webhook URL or paste it into chat.
pause
