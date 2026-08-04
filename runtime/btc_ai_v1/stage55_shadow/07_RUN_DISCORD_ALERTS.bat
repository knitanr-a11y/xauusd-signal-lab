@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python ..\..\..\scripts\btc_ai_v1\stage55_discord_notifier.py run-loop --config local_config.json
pause
