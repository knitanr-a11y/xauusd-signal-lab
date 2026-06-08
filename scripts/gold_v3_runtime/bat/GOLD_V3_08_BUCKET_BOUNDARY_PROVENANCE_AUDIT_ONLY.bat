@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v3_runtime\gold_v3_08_bucket_boundary_provenance_audit_only.py
endlocal
