@echo off
setlocal
cd /d "%~dp0"
if not exist local_config.json (
  echo local_config.json not found. Run 02_BOOTSTRAP_ACTIVATE.bat first.
  pause
  exit /b 1
)
notepad local_config.json
echo Set discord.enabled=true and paste the Webhook URL locally. Do not commit or paste it into chat.
pause
