@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v3_runtime\gold_v3_38_live_minute_loop.py --loop --enable-discord
pause
