@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_14b_coreb_cluster_source_read_and_replay_audit_only.py
pause
