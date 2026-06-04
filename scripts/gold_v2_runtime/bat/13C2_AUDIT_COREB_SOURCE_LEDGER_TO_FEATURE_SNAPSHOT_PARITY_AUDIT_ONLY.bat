@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_13c2_coreb_source_ledger_to_feature_snapshot_parity_audit_only.py
pause
