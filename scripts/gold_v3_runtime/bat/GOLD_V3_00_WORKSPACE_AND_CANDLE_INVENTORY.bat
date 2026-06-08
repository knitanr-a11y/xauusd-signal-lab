@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v3_runtime\gold_v3_00_workspace_and_candle_inventory.py
endlocal
