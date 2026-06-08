@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c100_entry_time_prefix_observability_audit_only.py
endlocal
