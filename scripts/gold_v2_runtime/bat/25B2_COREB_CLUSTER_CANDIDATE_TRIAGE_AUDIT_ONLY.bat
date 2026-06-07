@echo off
cd /d "%~dp0\..\..\.."
py scripts\gold_v2_runtime\audit_gold_v2_25b2_coreb_cluster_candidate_triage_audit_only.py
pause
