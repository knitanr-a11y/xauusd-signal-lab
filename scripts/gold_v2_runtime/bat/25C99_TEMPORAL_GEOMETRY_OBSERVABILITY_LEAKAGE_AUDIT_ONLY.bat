@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c99_temporal_geometry_observability_leakage_audit_only.py
endlocal
