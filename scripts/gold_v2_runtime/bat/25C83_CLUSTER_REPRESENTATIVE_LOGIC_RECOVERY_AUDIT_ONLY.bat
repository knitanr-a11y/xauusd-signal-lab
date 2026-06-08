@echo off
setlocal
cd /d "%~dp0\..\..\.."

python scripts\gold_v2_runtime\audit_gold_v2_25c83_cluster_representative_logic_recovery_audit_only.py

endlocal
