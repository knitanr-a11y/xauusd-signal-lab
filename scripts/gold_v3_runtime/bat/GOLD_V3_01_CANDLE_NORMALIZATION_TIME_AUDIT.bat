@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v3_runtime\gold_v3_01_candle_normalization_time_audit.py
endlocal
