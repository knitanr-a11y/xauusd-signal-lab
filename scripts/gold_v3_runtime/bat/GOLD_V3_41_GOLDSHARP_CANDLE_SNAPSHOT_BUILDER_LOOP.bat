@echo off
cd /d "%~dp0\..\..\.."
if exist "%APPDATA%\MetaQuotes\Terminal" (
  rem no-op
)
python scripts\gold_v3_runtime\gold_v3_41_goldsharp_candle_snapshot_builder.py --loop
pause
