@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c98_temporal_geometry_profit_collision_audit_only.py
endlocal
