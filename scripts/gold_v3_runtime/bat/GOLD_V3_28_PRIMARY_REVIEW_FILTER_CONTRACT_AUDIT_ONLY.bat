@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v3_runtime\gold_v3_28_primary_review_filter_contract_audit_only.py
pause
