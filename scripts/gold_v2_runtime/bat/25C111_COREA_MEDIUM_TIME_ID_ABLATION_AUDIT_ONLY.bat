@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c111_corea_medium_time_id_ablation_audit_only.py
endlocal
