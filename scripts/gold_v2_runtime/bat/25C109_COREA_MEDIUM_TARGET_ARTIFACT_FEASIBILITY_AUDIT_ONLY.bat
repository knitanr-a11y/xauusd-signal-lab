@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c109_corea_medium_target_artifact_feasibility_audit_only.py
endlocal
