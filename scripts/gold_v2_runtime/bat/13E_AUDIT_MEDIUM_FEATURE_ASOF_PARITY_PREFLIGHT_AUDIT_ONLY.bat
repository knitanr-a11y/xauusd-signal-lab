@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_13e_medium_feature_asof_parity_preflight_audit_only.py
pause
