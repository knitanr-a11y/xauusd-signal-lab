@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v3_runtime\gold_v3_04_entrytime_feature_matrix_audit_only.py
endlocal
