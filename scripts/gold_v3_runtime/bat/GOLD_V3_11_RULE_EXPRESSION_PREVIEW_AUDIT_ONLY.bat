@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v3_runtime\gold_v3_11_rule_expression_preview_audit_only.py
endlocal
