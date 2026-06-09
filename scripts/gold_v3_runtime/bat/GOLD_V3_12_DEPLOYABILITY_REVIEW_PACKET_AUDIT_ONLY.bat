@echo off
setlocal
cd /d "%~dp0\..\..\.."
python scripts\gold_v3_runtime\gold_v3_12_deployability_review_packet_audit_only.py
endlocal
