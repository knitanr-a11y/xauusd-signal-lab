@echo off
setlocal
title BTC Stage55 Shadow - Discord Status
cd /d "%~dp0"
echo ============================================================
echo BTC STAGE55 SHADOW - DISCORD NOTIFIER STATUS
echo ============================================================
call .venv\Scripts\activate.bat
python ..\..\..\scripts\btc_ai_v1\stage55_discord_notifier.py status --config local_config.json
pause
