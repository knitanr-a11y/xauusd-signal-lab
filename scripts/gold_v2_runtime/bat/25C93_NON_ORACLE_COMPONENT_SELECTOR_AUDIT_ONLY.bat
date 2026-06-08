@echo off
setlocal
cd /d "%~dp0\..\..\.."

python scripts\gold_v2_runtime\audit_gold_v2_25c93_non_oracle_component_selector_audit_only.py

endlocal
