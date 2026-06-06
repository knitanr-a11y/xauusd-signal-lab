@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\write_gold_v2_24h_human_decision_input.py --decision APPROVE_SOURCE_RECOVERY_EXECUTION --notes "selected by operator via helper bat; 24H validates for later routing audit only"
python scripts\gold_v2_runtime\audit_gold_v2_24h_source_recovery_execution_decision_intake_audit_only.py
pause
