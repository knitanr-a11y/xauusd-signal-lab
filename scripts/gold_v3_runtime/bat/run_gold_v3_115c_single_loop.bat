@echo off
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_115c_single_bat_loop.py --target-second 5 --retention-days 31
pause
