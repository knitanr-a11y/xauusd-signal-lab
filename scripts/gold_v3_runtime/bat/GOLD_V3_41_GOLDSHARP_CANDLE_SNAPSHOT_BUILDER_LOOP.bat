@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v3_runtime\gold_v3_41_goldsharp_candle_snapshot_builder.py --loop --delay-seconds 4
pause
