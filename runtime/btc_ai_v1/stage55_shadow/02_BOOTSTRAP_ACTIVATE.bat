@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
if not exist local_config.json (
  copy local_config.example.json local_config.json >nul
  notepad local_config.json
  echo Edit all four CSV paths, save, and run this file again.
  pause
  exit /b 1
)
python ..\..\..\scripts\btc_ai_v1\stage55_shadow_runtime.py --config local_config.json --activate
pause
