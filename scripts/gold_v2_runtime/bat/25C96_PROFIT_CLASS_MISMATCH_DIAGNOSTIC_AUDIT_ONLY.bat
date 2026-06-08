@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c96_profit_class_mismatch_diagnostic_audit_only.py
endlocal
