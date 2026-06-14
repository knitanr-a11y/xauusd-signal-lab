@echo off
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_107o_rolling_20d_adaptive_loss_trim_audit.py
pause
