@echo off
setlocal
title BTC Stage55 Shadow - Discord Test
cd /d "%~dp0"
echo ============================================================
echo BTC STAGE55 SHADOW - DISCORD CONNECTION TEST
echo Entry notification only / MT5 orders OFF
echo ============================================================
call .venv\Scripts\activate.bat
python ..\..\..\scripts\btc_ai_v1\stage55_discord_notifier.py test-discord --config local_config.json
echo.
echo [BTC_STAGE55_SHADOW] Discord test command finished.
pause
