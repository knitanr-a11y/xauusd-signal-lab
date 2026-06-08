@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v3_runtime\gold_v3_09_human_review_candidate_shortlist_audit_only.py
endlocal
