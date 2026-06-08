@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c97_profit_observability_ambiguity_audit_only.py
endlocal
