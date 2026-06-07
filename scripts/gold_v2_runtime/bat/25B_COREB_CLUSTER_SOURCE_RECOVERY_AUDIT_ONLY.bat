@echo off
cd /d "%~dp0\..\..\.."
py scripts\gold_v2_runtime\audit_gold_v2_25b_coreb_cluster_source_recovery_audit_only.py
pause
