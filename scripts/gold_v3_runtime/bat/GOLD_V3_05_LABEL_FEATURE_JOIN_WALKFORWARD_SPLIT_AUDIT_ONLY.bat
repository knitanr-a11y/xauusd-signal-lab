@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v3_runtime\gold_v3_05_label_feature_join_walkforward_split_audit_only.py
endlocal
