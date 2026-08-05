@echo off
setlocal
title BTC Stage55 Shadow - Discord Entry Alerts
cd /d "%~dp0"
echo ============================================================
echo BTC STAGE55 SHADOW - DISCORD ENTRY ALERT LOOP
echo Accepted entries only / Observation only / MT5 orders OFF
echo Close this window to stop Stage55 Discord notifications.
echo ============================================================
call .venv\Scripts\activate.bat
python ..\..\..\scripts\btc_ai_v1\stage55_discord_notifier.py run-loop --config local_config.json
pause
