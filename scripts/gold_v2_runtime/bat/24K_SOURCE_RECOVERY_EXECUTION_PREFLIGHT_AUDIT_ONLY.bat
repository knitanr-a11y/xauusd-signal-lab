@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_24k_source_recovery_execution_preflight_audit_only.py
pause
