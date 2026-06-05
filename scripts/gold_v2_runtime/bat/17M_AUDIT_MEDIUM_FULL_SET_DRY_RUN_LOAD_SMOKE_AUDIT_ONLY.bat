@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_17m_medium_full_set_dry_run_load_smoke_audit_only.py
pause
