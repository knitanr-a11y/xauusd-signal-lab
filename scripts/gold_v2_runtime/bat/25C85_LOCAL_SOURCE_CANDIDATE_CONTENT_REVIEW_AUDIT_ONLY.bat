@echo off
setlocal
cd /d "%~dp0\..\..\.."

python scripts\gold_v2_runtime\audit_gold_v2_25c85_local_source_candidate_content_review_audit_only.py

endlocal
