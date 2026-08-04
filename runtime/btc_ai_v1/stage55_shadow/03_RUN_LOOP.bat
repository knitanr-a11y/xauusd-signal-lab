@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
:loop
python ..\..\..\scripts\btc_ai_v1\stage55_shadow_runtime.py --config local_config.json
timeout /t 60 /nobreak >nul
goto loop
