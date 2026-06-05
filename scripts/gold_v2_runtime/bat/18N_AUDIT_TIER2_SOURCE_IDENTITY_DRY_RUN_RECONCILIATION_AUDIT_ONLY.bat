@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only.py
pause
