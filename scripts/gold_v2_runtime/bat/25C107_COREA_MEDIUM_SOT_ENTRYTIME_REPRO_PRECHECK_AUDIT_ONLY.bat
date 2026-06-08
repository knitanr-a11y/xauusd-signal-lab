@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c107_corea_medium_sot_entrytime_repro_precheck_audit_only.py
endlocal
