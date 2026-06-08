@echo off
setlocal
cd /d "%~dp0\..\..\.."

python scripts\gold_v2_runtime\audit_gold_v2_25c91_raw_cluster_parameter_sweep_audit_only.py

endlocal
