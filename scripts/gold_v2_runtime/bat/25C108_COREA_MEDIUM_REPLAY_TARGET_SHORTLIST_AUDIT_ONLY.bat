@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c108_corea_medium_replay_target_shortlist_audit_only.py
endlocal
