@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_only.py
pause
