@echo off
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_107p_rolling_lookback_parameter_sweep_audit.py
pause
