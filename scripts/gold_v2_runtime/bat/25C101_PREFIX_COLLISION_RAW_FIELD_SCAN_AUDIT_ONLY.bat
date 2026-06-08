@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c101_prefix_collision_raw_field_scan_audit_only.py
endlocal
