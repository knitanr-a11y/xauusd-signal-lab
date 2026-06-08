@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v3_runtime\gold_v3_02b_label_grid_contract_audit_only.py
endlocal
