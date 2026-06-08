@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v3_runtime\gold_v3_07_feature_bucket_lift_scan_audit_only.py
endlocal
