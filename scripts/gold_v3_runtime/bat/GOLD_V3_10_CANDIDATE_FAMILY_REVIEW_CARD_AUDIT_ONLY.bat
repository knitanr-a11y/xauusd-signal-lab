@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v3_runtime\gold_v3_10_candidate_family_review_card_audit_only.py
endlocal
