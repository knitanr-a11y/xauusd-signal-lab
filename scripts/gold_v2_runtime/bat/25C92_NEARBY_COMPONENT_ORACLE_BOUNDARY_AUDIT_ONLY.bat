@echo off
setlocal
cd /d "%~dp0\..\..\.."

python scripts\gold_v2_runtime\audit_gold_v2_25c92_nearby_component_oracle_boundary_audit_only.py

endlocal
