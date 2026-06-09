@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v3_runtime\gold_v3_40_mt5_demo_executor_loop.py --loop
pause
