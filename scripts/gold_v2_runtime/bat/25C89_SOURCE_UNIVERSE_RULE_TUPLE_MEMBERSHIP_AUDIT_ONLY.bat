@echo off
setlocal
cd /d "%~dp0\..\..\.."

python scripts\gold_v2_runtime\audit_gold_v2_25c89_source_universe_rule_tuple_membership_audit_only.py

endlocal
